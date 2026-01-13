# -*- coding: utf-8 -*-
"""
Multi-company tax declaration management and closing entries handling.

Features:
- Consolidated overview of all company declarations
- Multi-currency support with EUR conversion
- Closing entries detection and treatment
- Group-level reporting
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class BiztaxMultiCompanyManager(models.Model):
    """
    Manages tax declarations across multiple companies with consolidation view.
    """
    _name = 'biztax.multicompany.manager'
    _description = 'Gestionnaire multi-sociétés Biztax'
    _order = 'assessment_year desc, name'

    name = fields.Char(string='Référence', required=True)
    assessment_year = fields.Integer(
        string="Exercice d'imposition",
        required=True,
    )
    
    # Parent company / Group
    parent_company_id = fields.Many2one(
        'res.company',
        string='Société mère',
        required=True,
        domain="[('parent_id', '=', False)]",
    )
    
    # Child companies
    company_ids = fields.Many2many(
        'res.company',
        string='Sociétés du groupe',
        compute='_compute_company_ids',
        store=True,
    )
    
    # Declarations
    declaration_ids = fields.One2many(
        'biztax.declaration',
        'multicompany_manager_id',
        string='Déclarations',
    )
    declaration_count = fields.Integer(
        compute='_compute_declaration_stats',
    )
    
    # Consolidated amounts (in EUR)
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.ref('base.EUR'),
    )
    total_taxable_base = fields.Monetary(
        string='Base imposable totale',
        compute='_compute_consolidated_amounts',
        store=True,
        currency_field='currency_id',
    )
    total_tax_amount = fields.Monetary(
        string='Impôt total',
        compute='_compute_consolidated_amounts',
        store=True,
        currency_field='currency_id',
    )
    total_balance_due = fields.Monetary(
        string='Solde total',
        compute='_compute_consolidated_amounts',
        store=True,
        currency_field='currency_id',
    )
    
    # Status tracking
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('validated', 'Validé'),
        ('submitted', 'Soumis'),
    ], string='État', default='draft', compute='_compute_state', store=True)
    
    progress_percentage = fields.Float(
        compute='_compute_declaration_stats',
    )
    
    notes = fields.Text(string='Notes')

    @api.depends('parent_company_id')
    def _compute_company_ids(self):
        for rec in self:
            if rec.parent_company_id:
                # Get all child companies
                all_companies = self.env['res.company'].search([
                    '|',
                    ('id', '=', rec.parent_company_id.id),
                    ('parent_id', 'child_of', rec.parent_company_id.id),
                ])
                rec.company_ids = all_companies
            else:
                rec.company_ids = False

    @api.depends('declaration_ids', 'declaration_ids.state')
    def _compute_declaration_stats(self):
        for rec in self:
            rec.declaration_count = len(rec.declaration_ids)
            if rec.declaration_count > 0:
                submitted = len(rec.declaration_ids.filtered(lambda d: d.state == 'submitted'))
                rec.progress_percentage = (submitted / rec.declaration_count) * 100
            else:
                rec.progress_percentage = 0

    @api.depends('declaration_ids', 'declaration_ids.taxable_base', 
                 'declaration_ids.tax_amount', 'declaration_ids.balance_due',
                 'declaration_ids.currency_id')
    def _compute_consolidated_amounts(self):
        """Compute consolidated amounts with currency conversion to EUR"""
        eur = self.env.ref('base.EUR')
        for rec in self:
            total_base = 0
            total_tax = 0
            total_balance = 0
            
            for decl in rec.declaration_ids:
                # Convert to EUR if different currency
                if decl.currency_id and decl.currency_id != eur:
                    rate = decl.currency_id._get_conversion_rate(
                        decl.currency_id, eur,
                        decl.company_id, decl.fiscal_year_end
                    )
                    total_base += decl.taxable_base * rate
                    total_tax += decl.tax_amount * rate
                    total_balance += decl.balance_due * rate
                else:
                    total_base += decl.taxable_base or 0
                    total_tax += decl.tax_amount or 0
                    total_balance += decl.balance_due or 0
            
            rec.total_taxable_base = total_base
            rec.total_tax_amount = total_tax
            rec.total_balance_due = total_balance

    @api.depends('declaration_ids.state')
    def _compute_state(self):
        for rec in self:
            if not rec.declaration_ids:
                rec.state = 'draft'
            elif all(d.state == 'submitted' for d in rec.declaration_ids):
                rec.state = 'submitted'
            elif all(d.state in ('validated', 'generated', 'submitted') for d in rec.declaration_ids):
                rec.state = 'validated'
            elif any(d.state != 'draft' for d in rec.declaration_ids):
                rec.state = 'in_progress'
            else:
                rec.state = 'draft'

    def action_create_declarations(self):
        """Create declarations for all companies in the group"""
        self.ensure_one()
        
        for company in self.company_ids:
            # Check if declaration already exists
            existing = self.env['biztax.declaration'].search([
                ('company_id', '=', company.id),
                ('assessment_year', '=', self.assessment_year),
            ], limit=1)
            
            if not existing:
                # Determine fiscal year dates (default: calendar year before assessment year)
                fiscal_start = date(self.assessment_year - 1, 1, 1)
                fiscal_end = date(self.assessment_year - 1, 12, 31)
                
                self.env['biztax.declaration'].create({
                    'company_id': company.id,
                    'fiscal_year_start': fiscal_start,
                    'fiscal_year_end': fiscal_end,
                    'multicompany_manager_id': self.id,
                    'declaration_type': 'rcorp',
                })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Déclarations du groupe'),
            'res_model': 'biztax.declaration',
            'view_mode': 'list,form',
            'domain': [('multicompany_manager_id', '=', self.id)],
        }

    def action_view_declarations(self):
        """View all declarations for this group"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Déclarations - %s') % self.name,
            'res_model': 'biztax.declaration',
            'view_mode': 'list,form,kanban',
            'domain': [('multicompany_manager_id', '=', self.id)],
            'context': {'default_multicompany_manager_id': self.id},
        }


class BiztaxClosingEntry(models.Model):
    """
    Detect and manage year-end closing entries for tax purposes.
    Distinguishes between:
    - Accounting closing entries (to be ignored in tax calculation)
    - Fiscal closing entries (to be included)
    """
    _name = 'biztax.closing.entry'
    _description = 'Écriture de clôture Biztax'
    _order = 'date desc'

    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='declaration_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        related='declaration_id.currency_id',
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Pièce comptable',
        required=True,
    )
    date = fields.Date(
        related='move_id.date',
        store=True,
    )
    name = fields.Char(
        string='Libellé',
        related='move_id.name',
    )
    
    entry_type = fields.Selection([
        ('pnl_closing', 'Clôture résultat (6-7 → 14)'),
        ('allocation', 'Affectation résultat'),
        ('provision', 'Dotation/Reprise provision'),
        ('depreciation', 'Amortissement'),
        ('revaluation', 'Réévaluation'),
        ('tax_provision', 'Provision pour impôts'),
        ('deferred_tax', 'Impôts différés'),
        ('currency_adjustment', 'Écart de conversion'),
        ('consolidation', 'Écriture de consolidation'),
        ('other', 'Autre'),
    ], string='Type', required=True, default='other')
    
    fiscal_treatment = fields.Selection([
        ('include', 'Inclure dans le calcul fiscal'),
        ('exclude', 'Exclure du calcul fiscal'),
        ('adjust', 'Nécessite ajustement'),
        ('review', 'À vérifier manuellement'),
    ], string='Traitement fiscal', default='review')
    
    amount = fields.Monetary(
        string='Montant',
        currency_field='currency_id',
    )
    
    # Lines detail
    line_ids = fields.Many2many(
        'account.move.line',
        string='Lignes',
        compute='_compute_lines',
    )
    
    adjustment_id = fields.Many2one(
        'biztax.adjustment',
        string='Ajustement créé',
    )
    
    notes = fields.Text(string='Notes')
    processed = fields.Boolean(
        string='Traité',
        default=False,
    )

    @api.depends('move_id')
    def _compute_lines(self):
        for rec in self:
            rec.line_ids = rec.move_id.line_ids if rec.move_id else False

    @api.onchange('move_id')
    def _onchange_move_id(self):
        if self.move_id:
            self.amount = sum(abs(line.balance) for line in self.move_id.line_ids) / 2
            self._detect_entry_type()

    def _detect_entry_type(self):
        """Auto-detect the type of closing entry based on accounts used"""
        if not self.move_id:
            return
        
        accounts = self.move_id.line_ids.mapped('account_id.code')
        
        # P&L closing (class 6/7 to class 14)
        has_pnl = any(c and (c.startswith('6') or c.startswith('7')) for c in accounts)
        has_result = any(c and c.startswith('14') for c in accounts)
        if has_pnl and has_result:
            self.entry_type = 'pnl_closing'
            self.fiscal_treatment = 'exclude'
            return
        
        # Allocation (class 69 + 13/14)
        has_allocation = any(c and c.startswith('69') for c in accounts)
        has_reserves = any(c and c.startswith('13') for c in accounts)
        if has_allocation and has_reserves:
            self.entry_type = 'allocation'
            self.fiscal_treatment = 'include'
            return
        
        # Depreciation (class 63)
        if any(c and c.startswith('63') for c in accounts):
            self.entry_type = 'depreciation'
            self.fiscal_treatment = 'review'
            return
        
        # Provision (class 635/636/637)
        if any(c and c.startswith(('635', '636', '637')) for c in accounts):
            self.entry_type = 'provision'
            self.fiscal_treatment = 'adjust'
            return
        
        # Tax provision (class 67)
        if any(c and c.startswith('67') for c in accounts):
            self.entry_type = 'tax_provision'
            self.fiscal_treatment = 'review'
            return

    def action_create_adjustment(self):
        """Create fiscal adjustment based on this closing entry"""
        self.ensure_one()
        
        if self.fiscal_treatment != 'adjust':
            raise UserError(_("Cette écriture n'est pas marquée comme nécessitant un ajustement."))
        
        if self.adjustment_id:
            raise UserError(_("Un ajustement a déjà été créé pour cette écriture."))
        
        # Determine category and type based on entry_type
        category_map = {
            'provision': 'provision',
            'depreciation': 'depreciation',
            'revaluation': 'plus_value',
            'deferred_tax': 'other',
        }
        
        adjustment = self.env['biztax.adjustment'].create({
            'declaration_id': self.declaration_id.id,
            'name': f"Ajustement - {self.name}",
            'category': category_map.get(self.entry_type, 'other'),
            'adjustment_type': 'increase',
            'amount': self.amount,
            'move_line_ids': [(6, 0, self.line_ids.ids)],
            'notes': f"Créé depuis écriture de clôture: {self.move_id.name}",
        })
        
        self.adjustment_id = adjustment
        self.processed = True
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ajustement créé'),
            'res_model': 'biztax.adjustment',
            'res_id': adjustment.id,
            'view_mode': 'form',
        }


class BiztaxClosingDetectionWizard(models.TransientModel):
    """Wizard to detect and import closing entries"""
    _name = 'biztax.closing.detection.wizard'
    _description = 'Détection des écritures de clôture'

    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
    )
    
    detection_method = fields.Selection([
        ('date', 'Par date (dernier jour de l\'exercice)'),
        ('journal', 'Par journal (OD de clôture)'),
        ('ref', 'Par référence (contient "clôture")'),
        ('all', 'Toutes les méthodes'),
    ], string='Méthode de détection', default='all', required=True)
    
    closing_journal_ids = fields.Many2many(
        'account.journal',
        string='Journaux de clôture',
        domain="[('type', '=', 'general')]",
        help="Journaux utilisés pour les écritures de clôture",
    )
    
    detected_count = fields.Integer(
        string='Écritures détectées',
        readonly=True,
    )
    
    preview_ids = fields.Many2many(
        'account.move',
        string='Écritures détectées',
        readonly=True,
    )

    def action_detect(self):
        """Detect closing entries based on selected criteria"""
        self.ensure_one()
        decl = self.declaration_id
        
        domain = [
            ('company_id', '=', decl.company_id.id),
            ('state', '=', 'posted'),
            ('date', '>=', decl.fiscal_year_start),
            ('date', '<=', decl.fiscal_year_end),
        ]
        
        moves = self.env['account.move']
        
        if self.detection_method in ('date', 'all'):
            # Entries on last day of fiscal year
            date_moves = self.env['account.move'].search(
                domain + [('date', '=', decl.fiscal_year_end)]
            )
            moves |= date_moves
        
        if self.detection_method in ('journal', 'all') and self.closing_journal_ids:
            # Entries in closing journals
            journal_moves = self.env['account.move'].search(
                domain + [('journal_id', 'in', self.closing_journal_ids.ids)]
            )
            moves |= journal_moves
        
        if self.detection_method in ('ref', 'all'):
            # Entries with 'clôture' in reference
            ref_moves = self.env['account.move'].search(
                domain + ['|', 
                    ('ref', 'ilike', 'clôture'),
                    ('ref', 'ilike', 'cloture'),
                ]
            )
            moves |= ref_moves
        
        self.preview_ids = moves
        self.detected_count = len(moves)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Écritures détectées'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_import(self):
        """Import detected entries as closing entries"""
        self.ensure_one()
        
        created_count = 0
        for move in self.preview_ids:
            # Check if already imported
            existing = self.env['biztax.closing.entry'].search([
                ('declaration_id', '=', self.declaration_id.id),
                ('move_id', '=', move.id),
            ], limit=1)
            
            if not existing:
                entry = self.env['biztax.closing.entry'].create({
                    'declaration_id': self.declaration_id.id,
                    'move_id': move.id,
                })
                entry._detect_entry_type()
                created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import terminé'),
                'message': _('%d écritures de clôture importées') % created_count,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'name': _('Écritures de clôture'),
                    'res_model': 'biztax.closing.entry',
                    'view_mode': 'list,form',
                    'domain': [('declaration_id', '=', self.declaration_id.id)],
                },
            }
        }


# Extend the declaration model
class BiztaxDeclaration(models.Model):
    _inherit = 'biztax.declaration'

    multicompany_manager_id = fields.Many2one(
        'biztax.multicompany.manager',
        string='Gestionnaire groupe',
        ondelete='set null',
    )
    
    closing_entry_ids = fields.One2many(
        'biztax.closing.entry',
        'declaration_id',
        string='Écritures de clôture',
    )
    closing_entry_count = fields.Integer(
        compute='_compute_closing_entry_count',
    )
    
    extra_accounting_ids = fields.One2many(
        'biztax.extra.accounting',
        'declaration_id',
        string='Mouvements extra-comptables',
    )
    
    nid_calculation_id = fields.Many2one(
        'biztax.nid.calculation',
        string='Calcul NID',
        compute='_compute_nid_calculation',
    )
    
    # Currency conversion
    original_currency_id = fields.Many2one(
        'res.currency',
        string='Devise comptable',
        related='company_id.currency_id',
    )
    conversion_rate = fields.Float(
        string='Taux de conversion EUR',
        digits=(12, 6),
        default=1.0,
    )
    requires_conversion = fields.Boolean(
        string='Conversion requise',
        compute='_compute_requires_conversion',
    )

    @api.depends('closing_entry_ids')
    def _compute_closing_entry_count(self):
        for rec in self:
            rec.closing_entry_count = len(rec.closing_entry_ids)

    @api.depends('company_id.currency_id')
    def _compute_requires_conversion(self):
        eur = self.env.ref('base.EUR')
        for rec in self:
            rec.requires_conversion = rec.company_id.currency_id != eur

    def _compute_nid_calculation(self):
        for rec in self:
            rec.nid_calculation_id = self.env['biztax.nid.calculation'].search([
                ('declaration_id', '=', rec.id)
            ], limit=1)

    def action_view_closing_entries(self):
        """View closing entries for this declaration"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Écritures de clôture'),
            'res_model': 'biztax.closing.entry',
            'view_mode': 'list,form',
            'domain': [('declaration_id', '=', self.id)],
            'context': {'default_declaration_id': self.id},
        }

    def action_detect_closing_entries(self):
        """Open wizard to detect closing entries"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Détecter écritures de clôture'),
            'res_model': 'biztax.closing.detection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_declaration_id': self.id},
        }

    def action_calculate_nid(self):
        """Open or create NID calculation"""
        self.ensure_one()
        
        nid = self.env['biztax.nid.calculation'].search([
            ('declaration_id', '=', self.id)
        ], limit=1)
        
        if not nid:
            nid = self.env['biztax.nid.calculation'].create({
                'declaration_id': self.id,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Calcul intérêts notionnels'),
            'res_model': 'biztax.nid.calculation',
            'res_id': nid.id,
            'view_mode': 'form',
        }

    def _convert_to_eur(self, amount):
        """Convert amount to EUR using declaration date rate"""
        if not self.requires_conversion or not amount:
            return amount
        
        eur = self.env.ref('base.EUR')
        if self.conversion_rate:
            return amount * self.conversion_rate
        else:
            rate = self.original_currency_id._get_conversion_rate(
                self.original_currency_id, eur,
                self.company_id, self.fiscal_year_end
            )
            return amount * rate
