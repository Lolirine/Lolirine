# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BiztaxGenerateWizard(models.TransientModel):
    """Wizard to create a new Biztax declaration"""
    _name = 'biztax.generate.wizard'
    _description = 'Assistant de création de déclaration Biztax'

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    
    declaration_type = fields.Selection([
        ('rcorp', 'Impôt des sociétés (ISOC/VenB)'),
        ('rle', 'Impôt des personnes morales (IPM/RPB)'),
        ('nrcorp', 'Impôt des non-résidents/sociétés (INR/BNI)'),
    ], string='Type de déclaration', required=True, default='rcorp')
    
    taxonomy_version = fields.Selection([
        ('2025-04-30', 'be-tax-2025-04-30 (EI 2025)'),
        ('2024-04-30', 'be-tax-2024-04-30 (EI 2024)'),
    ], string='Version taxonomie', required=True, default='2025-04-30')
    
    # Fiscal year
    fiscal_year_start = fields.Date(
        string='Début exercice',
        required=True,
        default=lambda self: date(date.today().year - 1, 1, 1),
    )
    fiscal_year_end = fields.Date(
        string='Fin exercice',
        required=True,
        default=lambda self: date(date.today().year - 1, 12, 31),
    )
    assessment_year = fields.Integer(
        string='Exercice d\'imposition',
        compute='_compute_assessment_year',
    )
    
    @api.depends('fiscal_year_end')
    def _compute_assessment_year(self):
        for wizard in self:
            if wizard.fiscal_year_end:
                wizard.assessment_year = wizard.fiscal_year_end.year + 1
            else:
                wizard.assessment_year = date.today().year
    
    # Options
    import_accounting_data = fields.Boolean(
        string='Importer données comptables',
        default=True,
        help="Importer automatiquement les données depuis la comptabilité Odoo",
    )
    create_default_adjustments = fields.Boolean(
        string='Créer ajustements par défaut',
        default=True,
        help="Créer automatiquement les ajustements fiscaux courants",
    )
    
    # Info
    existing_declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration existante',
        compute='_compute_existing_declaration',
    )
    warning_message = fields.Char(
        compute='_compute_warning_message',
    )

    @api.depends('company_id', 'fiscal_year_start', 'fiscal_year_end', 'declaration_type')
    def _compute_existing_declaration(self):
        for wizard in self:
            existing = self.env['biztax.declaration'].search([
                ('company_id', '=', wizard.company_id.id),
                ('fiscal_year_start', '=', wizard.fiscal_year_start),
                ('fiscal_year_end', '=', wizard.fiscal_year_end),
                ('declaration_type', '=', wizard.declaration_type),
                ('state', '!=', 'cancelled'),
            ], limit=1)
            wizard.existing_declaration_id = existing

    @api.depends('existing_declaration_id')
    def _compute_warning_message(self):
        for wizard in self:
            if wizard.existing_declaration_id:
                wizard.warning_message = _(
                    "Une déclaration existe déjà pour cette période (%s). "
                    "Une nouvelle déclaration sera créée."
                ) % wizard.existing_declaration_id.name
            else:
                wizard.warning_message = False

    @api.onchange('fiscal_year_start')
    def _onchange_fiscal_year_start(self):
        if self.fiscal_year_start:
            # Default to 12-month period
            self.fiscal_year_end = self.fiscal_year_start + relativedelta(years=1, days=-1)

    def action_create_declaration(self):
        """Create the Biztax declaration"""
        self.ensure_one()
        
        # Create declaration
        declaration = self.env['biztax.declaration'].create({
            'company_id': self.company_id.id,
            'declaration_type': self.declaration_type,
            'taxonomy_version': self.taxonomy_version,
            'fiscal_year_start': self.fiscal_year_start,
            'fiscal_year_end': self.fiscal_year_end,
            'tax_rate': self.company_id.default_tax_rate or 25.0,
            'tax_rate_reduced': self.company_id.default_tax_rate_reduced or 20.0,
        })
        
        # Import accounting data if requested
        if self.import_accounting_data:
            declaration._import_accounting_data()
        
        # Create default adjustments if requested
        if self.create_default_adjustments:
            self._create_default_adjustments(declaration)
        
        # Update state if data was imported
        if self.import_accounting_data:
            declaration.state = 'computed'
        
        # Open the declaration
        return {
            'type': 'ir.actions.act_window',
            'name': _('Déclaration Biztax'),
            'res_model': 'biztax.declaration',
            'res_id': declaration.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_default_adjustments(self, declaration):
        """Create default fiscal adjustments"""
        # Get templates and create adjustments
        templates = self.env['biztax.adjustment.template'].search([])
        
        for template in templates:
            self.env['biztax.adjustment'].create({
                'declaration_id': declaration.id,
                'tax_code_id': template.tax_code_id.id,
                'name': template.name,
                'category': template.category,
                'adjustment_type': template.adjustment_type,
                'dna_percentage': template.default_dna_percentage,
                'amount': 0,  # To be filled manually
            })


class BiztaxRegenerateWizard(models.TransientModel):
    """Wizard to regenerate XBRL/Biztax files"""
    _name = 'biztax.regenerate.wizard'
    _description = 'Assistant de régénération Biztax'

    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
    )
    
    regenerate_xbrl = fields.Boolean(
        string='Régénérer XBRL',
        default=True,
    )
    regenerate_biztax = fields.Boolean(
        string='Régénérer .biztax',
        default=True,
    )
    include_attachments = fields.Boolean(
        string='Inclure les annexes',
        default=True,
    )

    def action_regenerate(self):
        """Regenerate the files"""
        self.ensure_one()
        
        declaration = self.declaration_id
        generator = self.env['biztax.xbrl.generator']
        
        if self.regenerate_xbrl:
            declaration.xbrl_file = False
            declaration.action_generate_xbrl()
        
        if self.regenerate_biztax:
            declaration.biztax_file = False
            if self.include_attachments:
                declaration.action_generate_biztax()
            else:
                # Generate without attachments
                # Temporarily remove attachments
                attachments = declaration.attachment_ids
                declaration.attachment_ids = False
                declaration.action_generate_biztax()
                declaration.attachment_ids = attachments
        
        return {'type': 'ir.actions.act_window_close'}
