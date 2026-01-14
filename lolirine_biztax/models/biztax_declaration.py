# -*- coding: utf-8 -*-
"""
Biztax Declaration Model - Complete Belgian corporate tax declaration
Generates XBRL compliant with be-tax taxonomy and .biztax package with annexes
"""
import base64
import io
import zipfile
import json
from datetime import date, datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiztaxDeclaration(models.Model):
    """
    Main Biztax declaration model.
    Represents a single ISOC/IPM/INR declaration for a fiscal year.
    Generates XBRL instance and .biztax package for MyMinfin submission.
    """
    _name = 'biztax.declaration'
    _description = 'Déclaration Biztax ISOC'
    _order = 'fiscal_year_end desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =========================================================================
    # IDENTIFICATION FIELDS
    # =========================================================================
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

    # =========================================================================
    # DECLARATION TYPE & STATUS
    # =========================================================================
    declaration_type = fields.Selection([
        ('rcorp', 'Impôt des sociétés (ISOC/VenB)'),
        ('rle', 'Impôt des personnes morales (IPM/RPB)'),
        ('nrcorp', 'Impôt des non-résidents/sociétés (INR/BNI)'),
    ], string='Type de déclaration', required=True, default='rcorp', tracking=True)
    
    declaration_status = fields.Selection([
        ('initial', 'Déclaration initiale'),
        ('corrective', 'Déclaration corrective'),
        ('nil', 'Déclaration néant'),
    ], string='Statut déclaration', required=True, default='initial', tracking=True,
       help="Initial = première déclaration, Corrective = modification d'une déclaration existante")
    
    corrected_declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration corrigée',
        help="Référence à la déclaration initiale en cas de correction",
    )
    
    taxonomy_version = fields.Selection([
        ('2025-04-30', 'be-tax-2025-04-30 (EI 2025)'),
        ('2024-04-30', 'be-tax-2024-04-30 (EI 2024)'),
        ('2023-04-30', 'be-tax-2023-04-30 (EI 2023)'),
    ], string='Version taxonomie', required=True, default='2025-04-30')

    # =========================================================================
    # FISCAL YEAR
    # =========================================================================
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
    
    fiscal_year_months = fields.Integer(
        string='Durée exercice (mois)',
        compute='_compute_fiscal_year_months',
        store=True,
    )

    # =========================================================================
    # COMPANY IDENTIFICATION (from res.company extension)
    # =========================================================================
    enterprise_number = fields.Char(
        string='Numéro d\'entreprise (BCE)',
        compute='_compute_company_info',
        store=True,
    )
    
    fiscal_number = fields.Char(
        string='Numéro fiscal',
        compute='_compute_company_info',
        store=True,
    )
    
    vat_number = fields.Char(
        string='Numéro TVA',
        related='company_id.vat',
        readonly=True,
    )
    
    legal_form = fields.Selection(
        related='company_id.legal_form',
        string='Forme juridique',
        readonly=True,
    )
    
    legal_form_code = fields.Char(
        related='company_id.legal_form_code',
        string='Code forme juridique',
        readonly=True,
    )
    
    registered_address = fields.Char(
        string='Adresse siège social',
        compute='_compute_company_info',
        store=True,
    )

    # =========================================================================
    # ACCOUNTING RESULT
    # =========================================================================
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
    
    # Detailed P&L from accounts
    total_revenue = fields.Monetary(
        string='Total produits (classe 7)',
        currency_field='currency_id',
        readonly=True,
    )
    
    total_expenses = fields.Monetary(
        string='Total charges (classe 6)',
        currency_field='currency_id',
        readonly=True,
    )

    # =========================================================================
    # ADJUSTMENTS (DNA, RDT, etc.)
    # =========================================================================
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
    
    # DNA specific totals
    total_dna = fields.Monetary(
        string='Total DNA',
        currency_field='currency_id',
        compute='_compute_category_totals',
        store=True,
    )
    
    total_rdt = fields.Monetary(
        string='Total RDT',
        currency_field='currency_id',
        compute='_compute_category_totals',
        store=True,
    )

    # =========================================================================
    # TAX CALCULATION
    # =========================================================================
    taxable_base = fields.Monetary(
        string='Base imposable',
        currency_field='currency_id',
        compute='_compute_taxable_base',
        store=True,
    )
    
    # Losses carried forward
    previous_losses = fields.Monetary(
        string='Pertes antérieures reportées',
        currency_field='currency_id',
        help="Pertes des exercices précédents déductibles",
    )
    
    losses_used = fields.Monetary(
        string='Pertes utilisées',
        currency_field='currency_id',
        compute='_compute_losses_used',
        store=True,
    )
    
    losses_remaining = fields.Monetary(
        string='Pertes reportables',
        currency_field='currency_id',
        compute='_compute_losses_used',
        store=True,
    )
    
    # Tax rates and calculation
    tax_rate = fields.Float(
        string='Taux normal (%)',
        default=25.0,
    )
    
    sme_rate = fields.Float(
        string='Taux PME (%)',
        default=20.0,
    )
    
    sme_threshold = fields.Float(
        string='Seuil PME (€)',
        default=100000.0,
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
    
    # Prepayments
    prepayments = fields.Monetary(
        string='Versements anticipés',
        currency_field='currency_id',
    )
    
    withholding_tax = fields.Monetary(
        string='Précomptes imputables',
        currency_field='currency_id',
    )
    
    tax_balance = fields.Monetary(
        string='Solde à payer/récupérer',
        currency_field='currency_id',
        compute='_compute_tax_balance',
        store=True,
    )

    # =========================================================================
    # ANNEXES / ATTACHMENTS
    # =========================================================================
    attachment_ids = fields.One2many(
        'biztax.attachment',
        'declaration_id',
        string='Annexes',
    )
    
    attachment_count = fields.Integer(
        string='Nombre d\'annexes',
        compute='_compute_attachment_count',
    )
    
    has_mandatory_annexes = fields.Boolean(
        string='Annexes obligatoires présentes',
        compute='_compute_mandatory_annexes',
    )
    
    missing_mandatory_annexes = fields.Char(
        string='Annexes manquantes',
        compute='_compute_mandatory_annexes',
    )

    # =========================================================================
    # GENERATED FILES
    # =========================================================================
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
    
    generation_date = fields.Datetime(
        string='Date génération',
        readonly=True,
    )
    
    submission_date = fields.Datetime(
        string='Date soumission',
        readonly=True,
    )
    
    submission_reference = fields.Char(
        string='Référence Biztax',
        help="Numéro de référence attribué par Biztax après soumission",
    )

    # =========================================================================
    # NOTES
    # =========================================================================
    notes = fields.Html(
        string='Notes internes',
    )

    # =========================================================================
    # COMPUTED METHODS
    # =========================================================================
    @api.depends('fiscal_year_end')
    def _compute_assessment_year(self):
        for record in self:
            if record.fiscal_year_end:
                record.assessment_year = record.fiscal_year_end.year + 1
            else:
                record.assessment_year = False
    
    @api.depends('fiscal_year_start', 'fiscal_year_end')
    def _compute_fiscal_year_months(self):
        for record in self:
            if record.fiscal_year_start and record.fiscal_year_end:
                delta = record.fiscal_year_end - record.fiscal_year_start
                record.fiscal_year_months = round(delta.days / 30)
            else:
                record.fiscal_year_months = 12
    
    @api.depends('company_id', 'company_id.bce_number', 'company_id.company_registry')
    def _compute_company_info(self):
        for record in self:
            company = record.company_id
            # Enterprise number: prefer bce_number field, fallback to company_registry
            record.enterprise_number = (
                company.bce_number or 
                company.company_registry or ''
            ).replace('.', '').replace(' ', '').replace('-', '')
            
            # Fiscal number
            record.fiscal_number = company.tax_identification_number or record.enterprise_number
            
            # Registered address
            if hasattr(company, 'get_registered_address'):
                addr = company.get_registered_address()
                parts = [addr.get('street', ''), addr.get('zip', ''), addr.get('city', '')]
                record.registered_address = ', '.join(filter(None, parts))
            else:
                record.registered_address = ''
    
    @api.depends('accounting_result')
    def _compute_accounting_result_type(self):
        for record in self:
            record.accounting_result_type = 'profit' if record.accounting_result >= 0 else 'loss'
    
    @api.depends('adjustment_ids.amount', 'adjustment_ids.adjustment_type')
    def _compute_totals(self):
        for record in self:
            increases = record.adjustment_ids.filtered(lambda a: a.adjustment_type == 'increase')
            decreases = record.adjustment_ids.filtered(lambda a: a.adjustment_type == 'decrease')
            record.total_increases = sum(increases.mapped('amount'))
            record.total_decreases = sum(decreases.mapped('amount'))
    
    @api.depends('adjustment_ids.amount', 'adjustment_ids.category')
    def _compute_category_totals(self):
        for record in self:
            dna_adjustments = record.adjustment_ids.filtered(lambda a: 'dna' in (a.category or ''))
            rdt_adjustments = record.adjustment_ids.filtered(lambda a: a.category == 'rdt')
            record.total_dna = sum(dna_adjustments.mapped('amount'))
            record.total_rdt = sum(rdt_adjustments.mapped('amount'))
    
    @api.depends('accounting_result', 'total_increases', 'total_decreases')
    def _compute_taxable_base(self):
        for record in self:
            record.taxable_base = max(0, (
                record.accounting_result + 
                record.total_increases - 
                record.total_decreases
            ))
    
    @api.depends('taxable_base', 'previous_losses')
    def _compute_losses_used(self):
        for record in self:
            if record.taxable_base > 0 and record.previous_losses > 0:
                # Maximum 70% of taxable base can be offset by losses (Belgian rule)
                max_deduction = record.taxable_base * 0.70
                record.losses_used = min(record.previous_losses, max_deduction)
                record.losses_remaining = record.previous_losses - record.losses_used
            else:
                record.losses_used = 0
                record.losses_remaining = record.previous_losses
    
    @api.depends('taxable_base', 'losses_used', 'tax_rate', 'sme_rate', 'sme_threshold', 'is_sme')
    def _compute_tax_due(self):
        for record in self:
            base_after_losses = max(0, record.taxable_base - record.losses_used)
            
            if base_after_losses <= 0:
                record.tax_due = 0
            elif record.is_sme:
                # SME rate: 20% on first 100.000€, 25% above
                if base_after_losses <= record.sme_threshold:
                    record.tax_due = base_after_losses * (record.sme_rate / 100)
                else:
                    record.tax_due = (
                        record.sme_threshold * (record.sme_rate / 100) + 
                        (base_after_losses - record.sme_threshold) * (record.tax_rate / 100)
                    )
            else:
                record.tax_due = base_after_losses * (record.tax_rate / 100)
    
    @api.depends('tax_due', 'prepayments', 'withholding_tax')
    def _compute_tax_balance(self):
        for record in self:
            record.tax_balance = record.tax_due - record.prepayments - record.withholding_tax
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)
    
    @api.depends('attachment_ids.annex_type')
    def _compute_mandatory_annexes(self):
        """Check if all mandatory annexes are present"""
        mandatory_types = ['275c']  # At minimum, 275C is required
        for record in self:
            present_types = record.attachment_ids.mapped('annex_type')
            missing = [t for t in mandatory_types if t not in present_types]
            record.has_mandatory_annexes = len(missing) == 0
            record.missing_mandatory_annexes = ', '.join(missing) if missing else ''

    # =========================================================================
    # CRUD METHODS
    # =========================================================================
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
                
                decl_type = vals.get('declaration_type', 'rcorp')
                type_prefix = {'rcorp': 'ISOC', 'rle': 'IPM', 'nrcorp': 'INR'}.get(decl_type, 'TAX')
                
                vals['name'] = f"{type_prefix}-{company.name[:10]}-{fiscal_year.year}"
        return super().create(vals_list)

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    def action_compute(self):
        """Compute accounting result from Odoo accounting"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Seules les déclarations en brouillon peuvent être calculées."))
        
        self._compute_accounting_result_from_accounts()
        self.state = 'computed'
        
        self.message_post(body=_("Déclaration calculée depuis la comptabilité Odoo"))
        return True
    
    def _compute_accounting_result_from_accounts(self):
        """Calculate accounting result from GL accounts (PCMN classes 6 & 7)"""
        self.ensure_one()
        
        MoveLine = self.env['account.move.line']
        
        base_domain = [
            ('date', '>=', self.fiscal_year_start),
            ('date', '<=', self.fiscal_year_end),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        
        # Class 7 - Revenue (credit balance = positive)
        revenue_lines = MoveLine.search(base_domain + [('account_id.code', '=like', '7%')])
        self.total_revenue = sum(revenue_lines.mapped('credit')) - sum(revenue_lines.mapped('debit'))
        
        # Class 6 - Expenses (debit balance = positive)
        expense_lines = MoveLine.search(base_domain + [('account_id.code', '=like', '6%')])
        self.total_expenses = sum(expense_lines.mapped('debit')) - sum(expense_lines.mapped('credit'))
        
        # Result = Revenue - Expenses
        self.accounting_result = self.total_revenue - self.total_expenses
    
    def action_validate(self):
        """Validate the declaration"""
        self.ensure_one()
        if self.state != 'computed':
            raise UserError(_("La déclaration doit d'abord être calculée."))
        
        # Validation checks
        if not self.enterprise_number:
            raise UserError(_("Le numéro d'entreprise (BCE) doit être configuré dans les paramètres société."))
        
        self.state = 'validated'
        self.message_post(body=_("Déclaration validée"))
        return True
    
    def action_generate_xbrl(self):
        """Generate XBRL instance file conforming to be-tax taxonomy"""
        self.ensure_one()
        if self.state not in ('validated', 'generated'):
            raise UserError(_("La déclaration doit d'abord être validée."))
        
        xbrl_content = self._generate_xbrl_content()
        
        self.xbrl_file = base64.b64encode(xbrl_content.encode('utf-8'))
        self.xbrl_filename = f"declaration_{self.name}_{self.assessment_year}.xbrl"
        self.generation_date = fields.Datetime.now()
        
        if self.state == 'validated':
            self.state = 'generated'
        
        self.message_post(body=_("Fichier XBRL généré: %s") % self.xbrl_filename)
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=biztax.declaration&id={self.id}&field=xbrl_file&filename_field=xbrl_filename&download=true',
            'target': 'self',
        }
    
    def _generate_xbrl_content(self):
        """Generate complete XBRL XML content conforming to be-tax taxonomy"""
        self.ensure_one()
        
        # Clean enterprise number
        enterprise = self.enterprise_number or '0000000000'
        
        # Taxonomy namespace based on version
        tax_ns = f"http://www.nbb.be/be/fr/pfs/ci/{self.taxonomy_version[:4]}"
        
        # Declaration type code
        decl_type_code = {
            'rcorp': 'RCORP',
            'rle': 'RLE', 
            'nrcorp': 'NRCORP'
        }.get(self.declaration_type, 'RCORP')
        
        # Build adjustment details for XBRL
        adjustment_elements = self._generate_xbrl_adjustments()
        
        xbrl = f"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:link="http://www.xbrl.org/2003/linkbase"
      xmlns:xlink="http://www.w3.org/1999/xlink"
      xmlns:iso4217="http://www.xbrl.org/2003/iso4217"
      xmlns:be-tax="{tax_ns}"
      xmlns:be-gcd="http://www.nbb.be/be/fr/pfs/gcd">

  <!-- ======================================================================= -->
  <!-- CONTEXTS -->
  <!-- ======================================================================= -->
  <context id="ctx_entity">
    <entity>
      <identifier scheme="http://www.kbo-bce.be">{enterprise}</identifier>
    </entity>
    <period>
      <instant>{self.fiscal_year_end}</instant>
    </period>
  </context>
  
  <context id="ctx_period">
    <entity>
      <identifier scheme="http://www.kbo-bce.be">{enterprise}</identifier>
    </entity>
    <period>
      <startDate>{self.fiscal_year_start}</startDate>
      <endDate>{self.fiscal_year_end}</endDate>
    </period>
  </context>

  <!-- ======================================================================= -->
  <!-- UNITS -->
  <!-- ======================================================================= -->
  <unit id="EUR">
    <measure>iso4217:EUR</measure>
  </unit>
  
  <unit id="pure">
    <measure>xbrli:pure</measure>
  </unit>

  <!-- ======================================================================= -->
  <!-- DECLARATION IDENTIFICATION -->
  <!-- ======================================================================= -->
  <be-gcd:EnterpriseNumber contextRef="ctx_entity">{enterprise}</be-gcd:EnterpriseNumber>
  <be-gcd:DeclarationType contextRef="ctx_entity">{decl_type_code}</be-gcd:DeclarationType>
  <be-gcd:DeclarationStatus contextRef="ctx_entity">{self.declaration_status.upper()}</be-gcd:DeclarationStatus>
  <be-gcd:AssessmentYear contextRef="ctx_entity">{self.assessment_year}</be-gcd:AssessmentYear>
  <be-gcd:FiscalYearStart contextRef="ctx_entity">{self.fiscal_year_start}</be-gcd:FiscalYearStart>
  <be-gcd:FiscalYearEnd contextRef="ctx_entity">{self.fiscal_year_end}</be-gcd:FiscalYearEnd>
  <be-gcd:FiscalYearMonths contextRef="ctx_entity" unitRef="pure">{self.fiscal_year_months}</be-gcd:FiscalYearMonths>
  
  <!-- Legal form -->
  <be-gcd:LegalFormCode contextRef="ctx_entity">{self.legal_form_code or '015'}</be-gcd:LegalFormCode>
  
  <!-- SME status -->
  <be-gcd:SMEStatus contextRef="ctx_entity">{'true' if self.is_sme else 'false'}</be-gcd:SMEStatus>

  <!-- ======================================================================= -->
  <!-- ACCOUNTING RESULT -->
  <!-- ======================================================================= -->
  <!-- Code 9903: Bénéfice/Perte de l'exercice -->
  <be-tax:Code9903 contextRef="ctx_period" unitRef="EUR" decimals="2">{self.accounting_result:.2f}</be-tax:Code9903>
  
  <!-- Detail: Total revenue -->
  <be-tax:TotalRevenue contextRef="ctx_period" unitRef="EUR" decimals="2">{self.total_revenue:.2f}</be-tax:TotalRevenue>
  
  <!-- Detail: Total expenses -->
  <be-tax:TotalExpenses contextRef="ctx_period" unitRef="EUR" decimals="2">{self.total_expenses:.2f}</be-tax:TotalExpenses>

  <!-- ======================================================================= -->
  <!-- FISCAL ADJUSTMENTS -->
  <!-- ======================================================================= -->
  <!-- Total increases (majorations) -->
  <be-tax:TotalIncreases contextRef="ctx_period" unitRef="EUR" decimals="2">{self.total_increases:.2f}</be-tax:TotalIncreases>
  
  <!-- Total decreases (diminutions) -->
  <be-tax:TotalDecreases contextRef="ctx_period" unitRef="EUR" decimals="2">{self.total_decreases:.2f}</be-tax:TotalDecreases>
  
  <!-- DNA total -->
  <be-tax:TotalDNA contextRef="ctx_period" unitRef="EUR" decimals="2">{self.total_dna:.2f}</be-tax:TotalDNA>
  
  <!-- RDT total -->
  <be-tax:TotalRDT contextRef="ctx_period" unitRef="EUR" decimals="2">{self.total_rdt:.2f}</be-tax:TotalRDT>
  
  <!-- Individual adjustments -->
{adjustment_elements}

  <!-- ======================================================================= -->
  <!-- TAX CALCULATION -->
  <!-- ======================================================================= -->
  <!-- Taxable base before losses -->
  <be-tax:TaxableBaseBeforeLosses contextRef="ctx_period" unitRef="EUR" decimals="2">{self.taxable_base:.2f}</be-tax:TaxableBaseBeforeLosses>
  
  <!-- Previous losses -->
  <be-tax:PreviousLosses contextRef="ctx_period" unitRef="EUR" decimals="2">{self.previous_losses:.2f}</be-tax:PreviousLosses>
  
  <!-- Losses deducted -->
  <be-tax:LossesDeducted contextRef="ctx_period" unitRef="EUR" decimals="2">{self.losses_used:.2f}</be-tax:LossesDeducted>
  
  <!-- Final taxable base -->
  <be-tax:TaxableBase contextRef="ctx_period" unitRef="EUR" decimals="2">{max(0, self.taxable_base - self.losses_used):.2f}</be-tax:TaxableBase>
  
  <!-- Tax rate -->
  <be-tax:TaxRate contextRef="ctx_period" unitRef="pure" decimals="2">{self.tax_rate:.2f}</be-tax:TaxRate>
  
  <!-- Tax due -->
  <be-tax:TaxDue contextRef="ctx_period" unitRef="EUR" decimals="2">{self.tax_due:.2f}</be-tax:TaxDue>
  
  <!-- Prepayments -->
  <be-tax:Prepayments contextRef="ctx_period" unitRef="EUR" decimals="2">{self.prepayments:.2f}</be-tax:Prepayments>
  
  <!-- Withholding tax -->
  <be-tax:WithholdingTax contextRef="ctx_period" unitRef="EUR" decimals="2">{self.withholding_tax:.2f}</be-tax:WithholdingTax>
  
  <!-- Balance -->
  <be-tax:TaxBalance contextRef="ctx_period" unitRef="EUR" decimals="2">{self.tax_balance:.2f}</be-tax:TaxBalance>

</xbrl>
"""
        return xbrl
    
    def _generate_xbrl_adjustments(self):
        """Generate XBRL elements for each adjustment"""
        elements = []
        for adj in self.adjustment_ids:
            tax_code = adj.tax_code_id.code if adj.tax_code_id else 'UNKNOWN'
            adj_type = 'INCREASE' if adj.adjustment_type == 'increase' else 'DECREASE'
            elements.append(f"""  <be-tax:Adjustment_{tax_code} contextRef="ctx_period" unitRef="EUR" decimals="2">{adj.amount:.2f}</be-tax:Adjustment_{tax_code}>
  <!-- {adj.name} - {adj_type} -->""")
        return '\n'.join(elements)
    
    def action_generate_biztax(self):
        """Generate .biztax package (ZIP file with XBRL + annexes + manifest)"""
        self.ensure_one()
        
        if self.state not in ('validated', 'generated'):
            raise UserError(_("La déclaration doit d'abord être validée."))
        
        # Generate XBRL if not already done
        if not self.xbrl_file:
            self.action_generate_xbrl()
        
        # Create ZIP package
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            manifest = self._generate_biztax_manifest()
            zf.writestr('manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False))
            
            # Add XBRL file
            xbrl_content = base64.b64decode(self.xbrl_file)
            zf.writestr(f'declaration.xbrl', xbrl_content)
            
            # Add PDF annexes
            for attachment in self.attachment_ids:
                if attachment.file_data:
                    pdf_content = base64.b64decode(attachment.file_data)
                    filename = attachment.get_biztax_filename()
                    zf.writestr(f'annexes/{filename}', pdf_content)
        
        # Save ZIP
        zip_buffer.seek(0)
        self.biztax_file = base64.b64encode(zip_buffer.read())
        self.biztax_filename = f"{self.name}_{self.assessment_year}.biztax"
        self.generation_date = fields.Datetime.now()
        
        if self.state == 'validated':
            self.state = 'generated'
        
        self.message_post(
            body=_("Fichier .biztax généré: %s (avec %d annexe(s))") % (
                self.biztax_filename, len(self.attachment_ids)
            )
        )
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=biztax.declaration&id={self.id}&field=biztax_file&filename_field=biztax_filename&download=true',
            'target': 'self',
        }
    
    def _generate_biztax_manifest(self):
        """Generate manifest.json for biztax package"""
        self.ensure_one()
        
        annexes_list = []
        for att in self.attachment_ids:
            annexes_list.append({
                'filename': att.get_biztax_filename(),
                'type': att.annex_type,
                'description': att.name,
                'mandatory': att.is_mandatory,
            })
        
        return {
            'version': '1.0',
            'generator': 'Odoo Lolirine Biztax Module',
            'generated_at': fields.Datetime.now().isoformat(),
            'declaration': {
                'type': self.declaration_type,
                'status': self.declaration_status,
                'assessment_year': self.assessment_year,
                'fiscal_year_start': str(self.fiscal_year_start),
                'fiscal_year_end': str(self.fiscal_year_end),
                'reference': self.name,
            },
            'entity': {
                'enterprise_number': self.enterprise_number,
                'fiscal_number': self.fiscal_number,
                'name': self.company_id.name,
                'legal_form': self.legal_form,
                'legal_form_code': self.legal_form_code,
                'address': self.registered_address,
            },
            'files': {
                'xbrl': 'declaration.xbrl',
                'annexes': annexes_list,
            },
            'taxonomy': {
                'version': self.taxonomy_version,
                'namespace': f"http://www.nbb.be/be/fr/pfs/ci/{self.taxonomy_version[:4]}",
            },
        }
    
    def action_mark_submitted(self):
        """Mark as submitted to Biztax"""
        self.ensure_one()
        if self.state != 'generated':
            raise UserError(_("Le fichier .biztax doit d'abord être généré."))
        
        self.state = 'submitted'
        self.submission_date = fields.Datetime.now()
        
        self.message_post(body=_("Déclaration marquée comme soumise à Biztax"))
        return True
    
    def action_reset_draft(self):
        """Reset to draft"""
        self.ensure_one()
        self.state = 'draft'
        self.xbrl_file = False
        self.xbrl_filename = False
        self.biztax_file = False
        self.biztax_filename = False
        return True
    
    def action_cancel(self):
        """Cancel the declaration"""
        self.ensure_one()
        self.state = 'cancelled'
        return True
    
    def action_view_attachments(self):
        """Open attachments view"""
        self.ensure_one()
        return {
            'name': _('Annexes'),
            'type': 'ir.actions.act_window',
            'res_model': 'biztax.attachment',
            'view_mode': 'list,form',
            'domain': [('declaration_id', '=', self.id)],
            'context': {'default_declaration_id': self.id},
        }
    
    # =========================================================================
    # AUTOMATIC ANNEXE GENERATION
    # =========================================================================
    
    def action_generate_all_annexes(self):
        """Generate all automatic annexes (Balance Sheet, P&L, DNA detail)"""
        self.ensure_one()
        
        generated = []
        
        # Check company settings
        company = self.company_id
        
        # Generate Balance Sheet if configured
        if company.biztax_include_balance_sheet:
            att = self._generate_annexe_from_report(
                'lolirine_biztax.action_report_balance_sheet',
                'balance_sheet',
                'Bilan'
            )
            if att:
                generated.append(att.name)
        
        # Generate Profit & Loss if configured
        if company.biztax_include_profit_loss:
            att = self._generate_annexe_from_report(
                'lolirine_biztax.action_report_profit_loss',
                'income_statement',
                'Compte de résultats'
            )
            if att:
                generated.append(att.name)
        
        # Generate DNA detail if there are DNA adjustments
        if self.total_dna > 0:
            att = self._generate_annexe_from_report(
                'lolirine_biztax.action_report_dna_detail',
                'dna_detail',
                'Détail des DNA'
            )
            if att:
                generated.append(att.name)
        
        # Generate Fiscal Summary
        att = self._generate_annexe_from_report(
            'lolirine_biztax.action_report_fiscal_summary',
            'other',
            'Résumé fiscal'
        )
        if att:
            generated.append(att.name)
        
        if generated:
            self.message_post(
                body=_("Annexes générées automatiquement: %s") % ', '.join(generated)
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Génération terminée'),
                'message': _('%d annexe(s) générée(s): %s') % (len(generated), ', '.join(generated)),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _generate_annexe_from_report(self, report_xml_id, annex_type, name):
        """
        Generate a PDF annexe from a QWeb report and attach it to the declaration
        
        :param report_xml_id: XML ID of the report action
        :param annex_type: Type code for biztax.attachment
        :param name: Display name for the attachment
        :return: Created biztax.attachment record or False
        """
        self.ensure_one()
        
        try:
            # Get the report action
            report = self.env.ref(report_xml_id)
            
            # Generate PDF content
            pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(
                report, [self.id]
            )
            
            # Check if attachment already exists for this type
            existing = self.attachment_ids.filtered(
                lambda a: a.annex_type == annex_type and a.generated_from_odoo
            )
            
            if existing:
                # Update existing attachment
                existing[0].write({
                    'file_data': base64.b64encode(pdf_content),
                    'file_name': f"{annex_type}_{self.name}_{self.assessment_year}.pdf",
                })
                return existing[0]
            else:
                # Create new attachment
                attachment = self.env['biztax.attachment'].create({
                    'name': name,
                    'declaration_id': self.id,
                    'annex_type': annex_type,
                    'file_data': base64.b64encode(pdf_content),
                    'file_name': f"{annex_type}_{self.name}_{self.assessment_year}.pdf",
                    'generated_from_odoo': True,
                    'source_report': report_xml_id,
                })
                return attachment
                
        except Exception as e:
            # Log error but don't fail the whole process
            self.message_post(
                body=_("Erreur lors de la génération de l'annexe '%s': %s") % (name, str(e)),
                message_type='notification'
            )
            return False
    
    def action_generate_balance_sheet(self):
        """Generate Balance Sheet PDF annexe"""
        self.ensure_one()
        att = self._generate_annexe_from_report(
            'lolirine_biztax.action_report_balance_sheet',
            'balance_sheet',
            'Bilan'
        )
        if att:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content?model=biztax.attachment&id={att.id}&field=file_data&filename_field=file_name&download=true',
                'target': 'self',
            }
    
    def action_generate_profit_loss(self):
        """Generate Profit & Loss PDF annexe"""
        self.ensure_one()
        att = self._generate_annexe_from_report(
            'lolirine_biztax.action_report_profit_loss',
            'income_statement',
            'Compte de résultats'
        )
        if att:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content?model=biztax.attachment&id={att.id}&field=file_data&filename_field=file_name&download=true',
                'target': 'self',
            }
    
    def action_generate_dna_detail(self):
        """Generate DNA Detail PDF annexe"""
        self.ensure_one()
        att = self._generate_annexe_from_report(
            'lolirine_biztax.action_report_dna_detail',
            'dna_detail',
            'Détail des DNA'
        )
        if att:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content?model=biztax.attachment&id={att.id}&field=file_data&filename_field=file_name&download=true',
                'target': 'self',
            }
    
    def action_generate_fiscal_summary(self):
        """Generate complete Fiscal Summary PDF"""
        self.ensure_one()
        att = self._generate_annexe_from_report(
            'lolirine_biztax.action_report_fiscal_summary',
            'other',
            'Résumé fiscal complet'
        )
        if att:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content?model=biztax.attachment&id={att.id}&field=file_data&filename_field=file_name&download=true',
                'target': 'self',
            }

