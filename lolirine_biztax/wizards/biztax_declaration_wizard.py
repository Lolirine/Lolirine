# -*- coding: utf-8 -*-
"""
Biztax Declaration Creation Wizard
"""
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BiztaxDeclarationWizard(models.TransientModel):
    """Wizard for creating a new Biztax declaration"""
    _name = 'biztax.declaration.wizard'
    _description = 'Assistant création déclaration Biztax'

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
    
    declaration_status = fields.Selection([
        ('initial', 'Déclaration initiale'),
        ('corrective', 'Déclaration corrective'),
        ('nil', 'Déclaration néant'),
    ], string='Statut', required=True, default='initial')
    
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
    
    taxonomy_version = fields.Selection([
        ('2025-04-30', 'be-tax-2025-04-30 (EI 2025)'),
        ('2024-04-30', 'be-tax-2024-04-30 (EI 2024)'),
    ], string='Version taxonomie', required=True, default='2025-04-30')
    
    is_sme = fields.Boolean(
        string='PME (taux réduit)',
        help="Éligible au taux réduit PME de 20% sur les premiers 100.000€",
    )
    
    create_standard_adjustments = fields.Boolean(
        string='Créer ajustements standards',
        default=True,
        help="Créer automatiquement les lignes d'ajustement standards (DNA restaurant, véhicules, etc.)",
    )

    @api.onchange('fiscal_year_start')
    def _onchange_fiscal_year_start(self):
        if self.fiscal_year_start:
            # Default to end of same year
            self.fiscal_year_end = date(
                self.fiscal_year_start.year, 12, 31
            )

    def action_create_declaration(self):
        """Create the declaration and optionally standard adjustments"""
        self.ensure_one()
        
        # Check if declaration already exists for this period
        existing = self.env['biztax.declaration'].search([
            ('company_id', '=', self.company_id.id),
            ('fiscal_year_start', '=', self.fiscal_year_start),
            ('fiscal_year_end', '=', self.fiscal_year_end),
            ('state', '!=', 'cancelled'),
        ], limit=1)
        
        if existing:
            raise UserError(_(
                "Une déclaration existe déjà pour cette période: %s"
            ) % existing.name)
        
        # Create declaration
        declaration = self.env['biztax.declaration'].create({
            'company_id': self.company_id.id,
            'declaration_type': self.declaration_type,
            'declaration_status': self.declaration_status,
            'fiscal_year_start': self.fiscal_year_start,
            'fiscal_year_end': self.fiscal_year_end,
            'taxonomy_version': self.taxonomy_version,
            'is_sme': self.is_sme,
        })
        
        # Create standard adjustments if requested
        if self.create_standard_adjustments:
            self._create_standard_adjustments(declaration)
        
        # Return action to view the declaration
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'biztax.declaration',
            'res_id': declaration.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_standard_adjustments(self, declaration):
        """Create standard adjustment lines"""
        Adjustment = self.env['biztax.adjustment']
        
        standard_adjustments = [
            {
                'name': 'DNA - Frais de restaurant (31%)',
                'category': 'dna_restaurant',
                'adjustment_type': 'increase',
                'dna_percentage': 31.0,
                'amount': 0,
                'legal_reference': 'Art. 53, 8° CIR92',
            },
            {
                'name': 'DNA - Frais de réception (50%)',
                'category': 'dna_reception',
                'adjustment_type': 'increase',
                'dna_percentage': 50.0,
                'amount': 0,
                'legal_reference': 'Art. 53, 8° CIR92',
            },
            {
                'name': 'DNA - Cadeaux d\'affaires (50%)',
                'category': 'dna_gifts',
                'adjustment_type': 'increase',
                'dna_percentage': 50.0,
                'amount': 0,
                'legal_reference': 'Art. 53, 9° CIR92',
            },
            {
                'name': 'DNA - Véhicules',
                'category': 'dna_vehicle',
                'adjustment_type': 'increase',
                'amount': 0,
                'legal_reference': 'Art. 66 CIR92',
            },
            {
                'name': 'DNA - Amendes et pénalités (100%)',
                'category': 'dna_fines',
                'adjustment_type': 'increase',
                'dna_percentage': 100.0,
                'amount': 0,
                'legal_reference': 'Art. 53, 6° CIR92',
            },
        ]
        
        for idx, adj_vals in enumerate(standard_adjustments):
            adj_vals['declaration_id'] = declaration.id
            adj_vals['sequence'] = (idx + 1) * 10
            Adjustment.create(adj_vals)
