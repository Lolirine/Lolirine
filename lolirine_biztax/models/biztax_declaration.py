# -*- coding: utf-8 -*-
"""
Biztax Declaration Model - Main declaration for Belgian corporate tax
"""
import base64
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiztaxDeclaration(models.Model):
    """
    Main Biztax declaration model.
    Represents a single ISOC declaration for a fiscal year.
    """
    _name = 'biztax.declaration'
    _description = 'Déclaration Biztax ISOC'
    _order = 'fiscal_year_end desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # IDENTIFICATION FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        default='/',
        copy=False,
        tracking=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('computed', 'Calculé'),
        ('validated', 'Validé'),
        ('generated', 'Fichier généré'),
        ('submitted', 'Soumis'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', tracking=True, copy=False)

    # -------------------------------------------------------------------------
    # DECLARATION TYPE
    # -------------------------------------------------------------------------
    declaration_type = fields.Selection([
        ('rcorp', 'Impôt des sociétés (ISOC/VenB)'),
        ('rle', 'Impôt des personnes morales (IPM/RPB)'),
        ('nrcorp', 'Impôt des non-résidents/sociétés (INR/BNI)'),
    ], string='Type de déclaration', required=True, default='rcorp', tracking=True)
    
    taxonomy_version = fields.Selection([
        ('2025-04-30', 'be-tax-2025-04-30 (EI 2025)'),
        ('2024-04-30', 'be-tax-2024-04-30 (EI 2024)'),
    ], string='Version taxonomie', required=True, default='2025-04-30')

    # -------------------------------------------------------------------------
    # FISCAL YEAR
    # -------------------------------------------------------------------------
    fiscal_year_start = fields.Date(
        string='Début exercice',
        required=True,
        tracking=True,
    )
    
    fiscal_year_end = fields.Date(
        string='Fin exercice',
        required=True,
        tracking=True,
    )
    
    assessment_year = fields.Integer(
        string='Exercice d\'imposition',
        compute='_compute_assessment_year',
        store=True,
        help="Année d'imposition (année suivant la clôture)",
    )

    # -------------------------------------------------------------------------
    # COMPANY INFO
    # -------------------------------------------------------------------------
    enterprise_number = fields.Char(
        string='Numéro d\'entreprise',
        related='company_id.company_registry',
        readonly=True,
    )
    
    vat_number = fields.Char(
        string='Numéro TVA',
        related='company_id.vat',
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # ACCOUNTING RESULT
    # -------------------------------------------------------------------------
    accounting_result = fields.Monetary(
        string='Résultat comptable',
        currency_field='currency_id',
        tracking=True,
        help="Bénéfice ou perte comptable de l'exercice (avant ajustements fiscaux)",
    )
    
    accounting_result_type = fields.Selection([
        ('profit', 'Bénéfice'),
        ('loss', 'Perte'),
    ], string='Type de résultat', compute='_compute_accounting_result_type', store=True)

    # -------------------------------------------------------------------------
    # ADJUSTMENTS
    # -------------------------------------------------------------------------
    adjustment_ids = fields.One2many(
        'biztax.adjustment',
        'declaration_id',
        string='Ajustements fiscaux',
    )
    
    total_increases = fields.Monetary(
        string='Total majorations',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )
    
    total_decreases = fields.Monetary(
        string='Total diminutions',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    # -------------------------------------------------------------------------
    # TAX CALCULATION
    # -------------------------------------------------------------------------
    taxable_base = fields.Monetary(
        string='Base imposable',
        currency_field='currency_id',
        compute='_compute_taxable_base',
        store=True,
    )
    
    tax_rate = fields.Float(
        string='Taux d\'imposition (%)',
        default=25.0,
        help="Taux normal ISOC: 25%, Taux PME: 20% sur première tranche",
    )
    
    is_sme = fields.Boolean(
        string='PME (taux réduit)',
        help="Éligible au taux réduit PME de 20% sur les premiers 100.000€",
    )
    
    tax_due = fields.Monetary(
        string='Impôt dû',
        currency_field='currency_id',
        compute='_compute_tax_due',
        store=True,
    )

    # -------------------------------------------------------------------------
    # GENERATED FILES
    # -------------------------------------------------------------------------
    xbrl_file = fields.Binary(
        string='Fichier XBRL',
        attachment=True,
    )
    xbrl_filename = fields.Char(string='Nom fichier XBRL')
    
    biztax_file = fields.Binary(
        string='Fichier .biztax',
        attachment=True,
    )
    biztax_filename = fields.Char(string='Nom fichier .biztax')

    # -------------------------------------------------------------------------
    # COMPUTED METHODS
    # -------------------------------------------------------------------------
    @api.depends('fiscal_year_end')
    def _compute_assessment_year(self):
        for record in self:
            if record.fiscal_year_end:
                record.assessment_year = record.fiscal_year_end.year + 1
            else:
                record.assessment_year = False
    
    @api.depends('accounting_result')
    def _compute_accounting_result_type(self):
        for record in self:
            if record.accounting_result >= 0:
                record.accounting_result_type = 'profit'
            else:
                record.accounting_result_type = 'loss'
    
    @api.depends('adjustment_ids.amount', 'adjustment_ids.adjustment_type')
    def _compute_totals(self):
        for record in self:
            increases = record.adjustment_ids.filtered(
                lambda a: a.adjustment_type == 'increase'
            )
            decreases = record.adjustment_ids.filtered(
                lambda a: a.adjustment_type == 'decrease'
            )
            record.total_increases = sum(increases.mapped('amount'))
            record.total_decreases = sum(decreases.mapped('amount'))
    
    @api.depends('accounting_result', 'total_increases', 'total_decreases')
    def _compute_taxable_base(self):
        for record in self:
            record.taxable_base = max(0, (
                record.accounting_result + 
                record.total_increases - 
                record.total_decreases
            ))
    
    @api.depends('taxable_base', 'tax_rate', 'is_sme')
    def _compute_tax_due(self):
        for record in self:
            if record.taxable_base <= 0:
                record.tax_due = 0
            elif record.is_sme and record.taxable_base > 0:
                # Taux PME: 20% sur premiers 100.000€, 25% au-delà
                sme_threshold = 100000
                if record.taxable_base <= sme_threshold:
                    record.tax_due = record.taxable_base * 0.20
                else:
                    record.tax_due = (
                        sme_threshold * 0.20 + 
                        (record.taxable_base - sme_threshold) * 0.25
                    )
            else:
                record.tax_due = record.taxable_base * (record.tax_rate / 100)

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                company = self.env['res.company'].browse(
                    vals.get('company_id', self.env.company.id)
                )
                fiscal_year = vals.get('fiscal_year_end', fields.Date.today())
                if isinstance(fiscal_year, str):
                    fiscal_year = fields.Date.from_string(fiscal_year)
                vals['name'] = f"ISOC-{company.name[:10]}-{fiscal_year.year}"
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_compute(self):
        """Compute accounting result from Odoo accounting"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Seules les déclarations en brouillon peuvent être calculées."))
        
        self._compute_accounting_result_from_accounts()
        self.state = 'computed'
        return True
    
    def _compute_accounting_result_from_accounts(self):
        """Calculate accounting result from GL accounts"""
        self.ensure_one()
        
        domain = [
            ('date', '>=', self.fiscal_year_start),
            ('date', '<=', self.fiscal_year_end),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        
        # Products (class 7)
        products = self.env['account.move.line'].search(
            domain + [('account_id.code', '=like', '7%')]
        )
        total_products = sum(products.mapped('credit')) - sum(products.mapped('debit'))
        
        # Charges (class 6)
        charges = self.env['account.move.line'].search(
            domain + [('account_id.code', '=like', '6%')]
        )
        total_charges = sum(charges.mapped('debit')) - sum(charges.mapped('credit'))
        
        self.accounting_result = total_products - total_charges
    
    def action_validate(self):
        """Validate the declaration"""
        self.ensure_one()
        if self.state != 'computed':
            raise UserError(_("La déclaration doit d'abord être calculée."))
        self.state = 'validated'
        return True
    
    def action_generate_xbrl(self):
        """Generate XBRL file"""
        self.ensure_one()
        if self.state not in ('validated', 'generated'):
            raise UserError(_("La déclaration doit d'abord être validée."))
        
        xbrl_content = self._generate_xbrl_content()
        
        self.xbrl_file = base64.b64encode(xbrl_content.encode('utf-8'))
        self.xbrl_filename = f"declaration_{self.name}_{self.assessment_year}.xbrl"
        self.state = 'generated'
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=biztax.declaration&id={self.id}&field=xbrl_file&filename_field=xbrl_filename&download=true',
            'target': 'self',
        }
    
    def _generate_xbrl_content(self):
        """Generate XBRL XML content"""
        self.ensure_one()
        
        enterprise = self.enterprise_number or 'UNKNOWN'
        enterprise = enterprise.replace('.', '').replace(' ', '')
        
        xbrl = f"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:be-tax="http://www.nbb.be/be/fr/pfs/ci/2024">
  <context id="ctx_current">
    <entity>
      <identifier scheme="http://www.nbb.be/bce">{enterprise}</identifier>
    </entity>
    <period>
      <startDate>{self.fiscal_year_start}</startDate>
      <endDate>{self.fiscal_year_end}</endDate>
    </period>
  </context>
  <unit id="EUR">
    <measure>iso4217:EUR</measure>
  </unit>
  
  <!-- Résultat comptable -->
  <be-tax:AccountingResult contextRef="ctx_current" unitRef="EUR" decimals="2">
    {self.accounting_result:.2f}
  </be-tax:AccountingResult>
  
  <!-- Total majorations -->
  <be-tax:TotalIncreases contextRef="ctx_current" unitRef="EUR" decimals="2">
    {self.total_increases:.2f}
  </be-tax:TotalIncreases>
  
  <!-- Total diminutions -->
  <be-tax:TotalDecreases contextRef="ctx_current" unitRef="EUR" decimals="2">
    {self.total_decreases:.2f}
  </be-tax:TotalDecreases>
  
  <!-- Base imposable -->
  <be-tax:TaxableBase contextRef="ctx_current" unitRef="EUR" decimals="2">
    {self.taxable_base:.2f}
  </be-tax:TaxableBase>
  
  <!-- Impôt dû -->
  <be-tax:TaxDue contextRef="ctx_current" unitRef="EUR" decimals="2">
    {self.tax_due:.2f}
  </be-tax:TaxDue>
  
</xbrl>
"""
        return xbrl
    
    def action_generate_biztax(self):
        """Generate .biztax file for MyMinfin submission"""
        self.ensure_one()
        
        if not self.xbrl_file:
            self.action_generate_xbrl()
        
        # For now, biztax file = xbrl file (simplified)
        # Full implementation would create a proper ZIP package
        self.biztax_file = self.xbrl_file
        self.biztax_filename = f"declaration_{self.name}_{self.assessment_year}.biztax"
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=biztax.declaration&id={self.id}&field=biztax_file&filename_field=biztax_filename&download=true',
            'target': 'self',
        }
    
    def action_mark_submitted(self):
        """Mark as submitted to Biztax"""
        self.ensure_one()
        self.state = 'submitted'
        return True
    
    def action_reset_draft(self):
        """Reset to draft"""
        self.ensure_one()
        self.state = 'draft'
        return True
    
    def action_cancel(self):
        """Cancel the declaration"""
        self.ensure_one()
        self.state = 'cancelled'
        return True
