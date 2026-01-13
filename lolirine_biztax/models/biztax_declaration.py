# -*- coding: utf-8 -*-
import base64
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiztaxDeclaration(models.Model):
    _name = 'biztax.declaration'
    _description = 'Déclaration Biztax'
    _order = 'fiscal_year_end desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # === IDENTIFICATION ===
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
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('computed', 'Calculé'),
        ('validated', 'Validé'),
        ('generated', 'Fichier généré'),
        ('submitted', 'Soumis'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', tracking=True, copy=False)

    # === TYPE DE DÉCLARATION ===
    declaration_type = fields.Selection([
        ('rcorp', 'Impôt des sociétés (ISOC/VenB)'),
        ('rle', 'Impôt des personnes morales (IPM/RPB)'),
        ('nrcorp', 'Impôt des non-résidents/sociétés (INR/BNI)'),
    ], string='Type de déclaration', required=True, default='rcorp', tracking=True)
    
    taxonomy_version = fields.Selection([
        ('2025-04-30', 'be-tax-2025-04-30 (EI 2025)'),
        ('2024-04-30', 'be-tax-2024-04-30 (EI 2024)'),
    ], string='Version taxonomie', required=True, default='2025-04-30')

    # === PÉRIODE FISCALE ===
    fiscal_year_start = fields.Date(
        string='Début exercice comptable',
        required=True,
        tracking=True,
    )
    fiscal_year_end = fields.Date(
        string='Fin exercice comptable',
        required=True,
        tracking=True,
    )
    assessment_year = fields.Integer(
        string="Exercice d'imposition",
        compute='_compute_assessment_year',
        store=True,
    )
    
    # === DONNÉES SOCIÉTÉ ===
    vat_number = fields.Char(
        string='Numéro TVA',
        related='company_id.vat',
        readonly=True,
    )
    enterprise_number = fields.Char(
        string="Numéro d'entreprise (BCE)",
        compute='_compute_enterprise_number',
        store=True,
    )

    # === DONNÉES COMPTABLES BRUTES ===
    # Résultat comptable
    accounting_profit = fields.Monetary(
        string='Bénéfice comptable',
        currency_field='currency_id',
        tracking=True,
    )
    accounting_loss = fields.Monetary(
        string='Perte comptable',
        currency_field='currency_id',
        tracking=True,
    )
    
    # Réserves
    reserves_start = fields.Monetary(
        string='Réserves début exercice',
        currency_field='currency_id',
    )
    reserves_end = fields.Monetary(
        string='Réserves fin exercice',
        currency_field='currency_id',
    )
    reserves_movement = fields.Monetary(
        string='Mouvement des réserves',
        compute='_compute_reserves_movement',
        store=True,
        currency_field='currency_id',
    )
    
    # Dividendes et tantièmes
    dividends_distributed = fields.Monetary(
        string='Dividendes distribués',
        currency_field='currency_id',
    )
    tantiemes = fields.Monetary(
        string='Tantièmes',
        currency_field='currency_id',
    )

    # === AJUSTEMENTS FISCAUX ===
    adjustment_ids = fields.One2many(
        'biztax.adjustment',
        'declaration_id',
        string='Ajustements fiscaux',
    )
    
    # DNA - Dépenses Non Admises
    total_dna = fields.Monetary(
        string='Total DNA',
        compute='_compute_dna_totals',
        store=True,
        currency_field='currency_id',
    )
    
    # Déductions
    total_deductions = fields.Monetary(
        string='Total déductions',
        compute='_compute_deduction_totals',
        store=True,
        currency_field='currency_id',
    )

    # === CALCUL IMPÔT ===
    # Première opération
    first_operation_result = fields.Monetary(
        string='Résultat 1ère opération',
        compute='_compute_tax_calculation',
        store=True,
        currency_field='currency_id',
    )
    
    # Base imposable
    taxable_base = fields.Monetary(
        string='Base imposable',
        compute='_compute_tax_calculation',
        store=True,
        currency_field='currency_id',
    )
    
    # Impôt
    tax_rate = fields.Float(
        string='Taux ISOC (%)',
        default=25.0,
    )
    tax_rate_reduced = fields.Float(
        string='Taux réduit PME (%)',
        default=20.0,
    )
    is_sme = fields.Boolean(
        string='PME (taux réduit)',
        compute='_compute_is_sme',
        store=True,
    )
    tax_amount = fields.Monetary(
        string='Impôt calculé',
        compute='_compute_tax_calculation',
        store=True,
        currency_field='currency_id',
    )
    
    # Versements anticipés
    prepayments = fields.Monetary(
        string='Versements anticipés (VA)',
        currency_field='currency_id',
    )
    prepayment_benefit = fields.Monetary(
        string='Bonification VA',
        compute='_compute_prepayment_benefit',
        store=True,
        currency_field='currency_id',
    )
    
    # Solde à payer/récupérer
    balance_due = fields.Monetary(
        string='Solde à payer (+) / récupérer (-)',
        compute='_compute_balance',
        store=True,
        currency_field='currency_id',
    )

    # === PIÈCES JOINTES ===
    attachment_ids = fields.One2many(
        'biztax.attachment',
        'declaration_id',
        string='Annexes',
    )
    attachment_count = fields.Integer(
        compute='_compute_attachment_count',
    )

    # === FICHIERS GÉNÉRÉS ===
    xbrl_file = fields.Binary(
        string='Fichier XBRL',
        attachment=True,
        copy=False,
    )
    xbrl_filename = fields.Char(
        string='Nom fichier XBRL',
        copy=False,
    )
    biztax_file = fields.Binary(
        string='Fichier .biztax',
        attachment=True,
        copy=False,
    )
    biztax_filename = fields.Char(
        string='Nom fichier .biztax',
        copy=False,
    )
    
    # === VALIDATION ===
    validation_errors = fields.Text(
        string='Erreurs de validation',
        readonly=True,
    )
    is_valid = fields.Boolean(
        string='Validé XBRL',
        default=False,
    )

    # === COMMON ===
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.ref('base.EUR'),
    )
    notes = fields.Html(string='Notes')

    # === CONSTRAINTS ===
    @api.constrains('fiscal_year_start', 'fiscal_year_end')
    def _check_fiscal_year_dates(self):
        for record in self:
            if record.fiscal_year_start and record.fiscal_year_end:
                if record.fiscal_year_start >= record.fiscal_year_end:
                    raise ValidationError(_("La date de fin doit être postérieure à la date de début."))
                # Max 1 year + some tolerance for leap years etc.
                delta = (record.fiscal_year_end - record.fiscal_year_start).days
                if delta > 400:
                    raise ValidationError(_("L'exercice comptable ne peut pas dépasser 12 mois."))

    # === COMPUTE METHODS ===
    @api.depends('fiscal_year_end')
    def _compute_assessment_year(self):
        for record in self:
            if record.fiscal_year_end:
                # L'exercice d'imposition est généralement l'année suivant la clôture
                # pour une clôture au 31/12, EI = année + 1
                record.assessment_year = record.fiscal_year_end.year + 1
            else:
                record.assessment_year = False

    @api.depends('vat_number')
    def _compute_enterprise_number(self):
        for record in self:
            if record.vat_number:
                # Extraire le numéro d'entreprise du numéro TVA belge (BE0xxx.xxx.xxx)
                vat = record.vat_number.upper().replace(' ', '').replace('.', '')
                if vat.startswith('BE'):
                    record.enterprise_number = vat[2:]
                else:
                    record.enterprise_number = vat
            else:
                record.enterprise_number = False

    @api.depends('reserves_start', 'reserves_end')
    def _compute_reserves_movement(self):
        for record in self:
            record.reserves_movement = record.reserves_end - record.reserves_start

    @api.depends('adjustment_ids.amount', 'adjustment_ids.adjustment_type', 'adjustment_ids.category')
    def _compute_dna_totals(self):
        for record in self:
            dna_adjustments = record.adjustment_ids.filtered(
                lambda a: a.category == 'dna' and a.adjustment_type == 'increase'
            )
            record.total_dna = sum(dna_adjustments.mapped('amount'))

    @api.depends('adjustment_ids.amount', 'adjustment_ids.adjustment_type', 'adjustment_ids.category')
    def _compute_deduction_totals(self):
        for record in self:
            deductions = record.adjustment_ids.filtered(
                lambda a: a.category in ('deduction', 'exemption') and a.adjustment_type == 'decrease'
            )
            record.total_deductions = sum(deductions.mapped('amount'))

    @api.depends('company_id', 'company_id.employee_count')
    def _compute_is_sme(self):
        """
        PME au sens fiscal belge (Art. 15 CDE):
        - Ne dépasse pas plus d'un des critères suivants:
          - Effectif moyen annuel: 50 travailleurs
          - Chiffre d'affaires HTVA: 9.000.000 EUR
          - Total bilan: 4.500.000 EUR
        - Sauf si l'effectif > 100
        """
        for record in self:
            # Simplified check - in reality needs more data
            record.is_sme = True  # Default to SME, user can override

    @api.depends(
        'accounting_profit', 'accounting_loss',
        'reserves_movement', 'dividends_distributed', 'tantiemes',
        'total_dna', 'total_deductions',
        'is_sme', 'tax_rate', 'tax_rate_reduced'
    )
    def _compute_tax_calculation(self):
        for record in self:
            # 1ère opération: Résultat fiscal
            # Bénéfice comptable (ou perte) + réserves + dividendes + tantièmes
            result = (
                (record.accounting_profit or 0) - (record.accounting_loss or 0)
                + record.reserves_movement
                + (record.dividends_distributed or 0)
                + (record.tantiemes or 0)
            )
            record.first_operation_result = result
            
            # 2ème opération: Ajustements
            # + DNA - Déductions
            taxable = result + record.total_dna - record.total_deductions
            record.taxable_base = max(0, taxable)
            
            # Calcul de l'impôt
            if record.is_sme and record.taxable_base <= 100000:
                # Taux réduit PME sur première tranche de 100.000 EUR
                tax = record.taxable_base * (record.tax_rate_reduced / 100)
            elif record.is_sme and record.taxable_base > 100000:
                # Taux réduit sur 100.000 + taux normal sur le surplus
                tax = 100000 * (record.tax_rate_reduced / 100)
                tax += (record.taxable_base - 100000) * (record.tax_rate / 100)
            else:
                tax = record.taxable_base * (record.tax_rate / 100)
            
            record.tax_amount = tax

    @api.depends('prepayments', 'tax_amount')
    def _compute_prepayment_benefit(self):
        """Calcul simplifié de la bonification pour versements anticipés"""
        for record in self:
            # Taux de bonification 2024-2025 (simplifié)
            if record.prepayments:
                # Les taux réels varient selon les trimestres
                avg_rate = 0.045  # ~4.5% en moyenne
                record.prepayment_benefit = record.prepayments * avg_rate
            else:
                record.prepayment_benefit = 0

    @api.depends('tax_amount', 'prepayments', 'prepayment_benefit')
    def _compute_balance(self):
        for record in self:
            record.balance_due = (
                record.tax_amount 
                - (record.prepayments or 0) 
                - record.prepayment_benefit
            )

    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    # === CRUD METHODS ===
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('biztax.declaration') or '/'
        return super().create(vals_list)

    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'name': '/',
            'state': 'draft',
            'xbrl_file': False,
            'biztax_file': False,
            'validation_errors': False,
            'is_valid': False,
        })
        return super().copy(default)

    # === ACTION METHODS ===
    def action_compute(self):
        """Calculer les données fiscales depuis la comptabilité"""
        self.ensure_one()
        if self.state not in ('draft',):
            raise UserError(_("Seules les déclarations en brouillon peuvent être calculées."))
        
        self._import_accounting_data()
        self.state = 'computed'
        return True

    def action_validate(self):
        """Valider la déclaration"""
        self.ensure_one()
        if self.state not in ('computed',):
            raise UserError(_("Veuillez d'abord calculer la déclaration."))
        
        errors = self._validate_declaration()
        if errors:
            self.validation_errors = '\n'.join(errors)
            self.is_valid = False
            raise UserError(_("Erreurs de validation:\n%s") % '\n'.join(errors))
        
        self.validation_errors = False
        self.is_valid = True
        self.state = 'validated'
        return True

    def action_generate_xbrl(self):
        """Générer le fichier XBRL"""
        self.ensure_one()
        if self.state not in ('validated',):
            raise UserError(_("Veuillez d'abord valider la déclaration."))
        
        generator = self.env['biztax.xbrl.generator']
        xbrl_content = generator.generate_xbrl(self)
        
        filename = f"biztax_{self.enterprise_number}_{self.assessment_year}.xbrl"
        self.xbrl_file = base64.b64encode(xbrl_content.encode('utf-8'))
        self.xbrl_filename = filename
        
        return True

    def action_generate_biztax(self):
        """Générer le fichier .biztax complet"""
        self.ensure_one()
        if not self.xbrl_file:
            self.action_generate_xbrl()
        
        generator = self.env['biztax.xbrl.generator']
        biztax_content = generator.generate_biztax_package(self)
        
        filename = f"biztax_{self.enterprise_number}_{self.assessment_year}.biztax"
        self.biztax_file = base64.b64encode(biztax_content)
        self.biztax_filename = filename
        self.state = 'generated'
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/biztax.declaration/{self.id}/biztax_file/{filename}?download=true',
            'target': 'new',
        }

    def action_mark_submitted(self):
        """Marquer comme soumis (après dépôt manuel dans Biztax)"""
        self.ensure_one()
        if self.state not in ('generated',):
            raise UserError(_("Veuillez d'abord générer le fichier .biztax."))
        self.state = 'submitted'
        return True

    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.ensure_one()
        if self.state == 'submitted':
            raise UserError(_("Une déclaration soumise ne peut pas être remise en brouillon."))
        self.state = 'draft'
        self.xbrl_file = False
        self.biztax_file = False
        self.validation_errors = False
        self.is_valid = False
        return True

    def action_cancel(self):
        """Annuler la déclaration"""
        self.ensure_one()
        if self.state == 'submitted':
            raise UserError(_("Une déclaration soumise ne peut pas être annulée directement."))
        self.state = 'cancelled'
        return True

    def action_view_attachments(self):
        """Voir les pièces jointes"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Annexes'),
            'res_model': 'biztax.attachment',
            'view_mode': 'list,form',
            'domain': [('declaration_id', '=', self.id)],
            'context': {'default_declaration_id': self.id},
        }

    # === BUSINESS LOGIC ===
    def _import_accounting_data(self):
        """Import accounting data from Odoo accounting module"""
        self.ensure_one()
        
        # Get account move lines for the fiscal year
        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.fiscal_year_start),
            ('date', '<=', self.fiscal_year_end),
            ('parent_state', '=', 'posted'),
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        
        # Calculate profit/loss from P&L accounts (6xxx and 7xxx in Belgium)
        pnl_lines = move_lines.filtered(
            lambda l: l.account_id.code and (
                l.account_id.code.startswith('6') or 
                l.account_id.code.startswith('7')
            )
        )
        
        # Produits (classe 7) - Charges (classe 6)
        revenue = sum(pnl_lines.filtered(
            lambda l: l.account_id.code.startswith('7')
        ).mapped('credit')) - sum(pnl_lines.filtered(
            lambda l: l.account_id.code.startswith('7')
        ).mapped('debit'))
        
        expenses = sum(pnl_lines.filtered(
            lambda l: l.account_id.code.startswith('6')
        ).mapped('debit')) - sum(pnl_lines.filtered(
            lambda l: l.account_id.code.startswith('6')
        ).mapped('credit'))
        
        result = revenue - expenses
        
        if result >= 0:
            self.accounting_profit = result
            self.accounting_loss = 0
        else:
            self.accounting_profit = 0
            self.accounting_loss = abs(result)
        
        # Get reserves from balance sheet (class 13 in Belgium)
        # Start of year
        reserve_lines_start = self.env['account.move.line'].search([
            ('company_id', '=', self.company_id.id),
            ('date', '<', self.fiscal_year_start),
            ('parent_state', '=', 'posted'),
            ('account_id.code', '=like', '13%'),
        ])
        self.reserves_start = sum(reserve_lines_start.mapped('credit')) - sum(reserve_lines_start.mapped('debit'))
        
        # End of year
        reserve_lines_end = self.env['account.move.line'].search([
            ('company_id', '=', self.company_id.id),
            ('date', '<=', self.fiscal_year_end),
            ('parent_state', '=', 'posted'),
            ('account_id.code', '=like', '13%'),
        ])
        self.reserves_end = sum(reserve_lines_end.mapped('credit')) - sum(reserve_lines_end.mapped('debit'))
        
        # Dividends (account 694 typically)
        dividend_lines = move_lines.filtered(
            lambda l: l.account_id.code and l.account_id.code.startswith('694')
        )
        self.dividends_distributed = sum(dividend_lines.mapped('debit'))
        
        # Tantièmes (account 695 typically)
        tantieme_lines = move_lines.filtered(
            lambda l: l.account_id.code and l.account_id.code.startswith('695')
        )
        self.tantiemes = sum(tantieme_lines.mapped('debit'))
        
        # Import DNA from mapped accounts
        self._import_dna_from_accounts(move_lines)
        
        return True

    def _import_dna_from_accounts(self, move_lines):
        """Import DNA (Dépenses Non Admises) from account mappings"""
        mappings = self.env['biztax.account.mapping'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ])
        
        for mapping in mappings:
            if mapping.account_id:
                account_lines = move_lines.filtered(
                    lambda l: l.account_id.id == mapping.account_id.id
                )
            elif mapping.account_code_prefix:
                account_lines = move_lines.filtered(
                    lambda l: l.account_id.code and 
                    l.account_id.code.startswith(mapping.account_code_prefix)
                )
            else:
                continue
            
            amount = sum(account_lines.mapped('debit')) - sum(account_lines.mapped('credit'))
            
            if amount and mapping.dna_percentage:
                dna_amount = amount * (mapping.dna_percentage / 100)
                
                # Create or update adjustment
                existing = self.adjustment_ids.filtered(
                    lambda a: a.tax_code_id.id == mapping.tax_code_id.id and a.auto_imported
                )
                if existing:
                    existing.amount = dna_amount
                else:
                    self.env['biztax.adjustment'].create({
                        'declaration_id': self.id,
                        'tax_code_id': mapping.tax_code_id.id,
                        'name': mapping.name or mapping.tax_code_id.name,
                        'category': 'dna',
                        'adjustment_type': 'increase',
                        'amount': dna_amount,
                        'auto_imported': True,
                    })

    def _validate_declaration(self):
        """Validate declaration before XBRL generation"""
        errors = []
        
        if not self.company_id.vat:
            errors.append(_("Le numéro de TVA de la société est obligatoire."))
        
        if not self.fiscal_year_start or not self.fiscal_year_end:
            errors.append(_("Les dates de l'exercice comptable sont obligatoires."))
        
        if self.accounting_profit == 0 and self.accounting_loss == 0:
            errors.append(_("Le résultat comptable ne peut pas être nul."))
        
        # Check required XBRL fields based on declaration type
        # This would check against the taxonomy requirements
        
        return errors
