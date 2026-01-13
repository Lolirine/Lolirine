# -*- coding: utf-8 -*-
"""
Detailed extra-accounting movements management for Belgian tax declarations.

Handles:
- Reintegrations (DNA with detailed categories)
- Fiscal depreciation vs accounting depreciation
- Non-deductible provisions
- Capital gains with different tax regimes
- RDT (Revenus Définitivement Taxés)
- NID (Notional Interest Deduction)
- Loss carryforward with Belgian basket rules
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class BiztaxExtraAccounting(models.Model):
    """
    Detailed tracking of extra-accounting fiscal adjustments.
    Each record represents a specific fiscal treatment different from accounting.
    """
    _name = 'biztax.extra.accounting'
    _description = 'Mouvement extra-comptable'
    _order = 'declaration_id, category, sequence'
    _inherit = ['mail.thread']

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
    sequence = fields.Integer(default=10)
    
    name = fields.Char(string='Libellé', required=True)
    
    category = fields.Selection([
        # Majorations - Première opération
        ('first_increase', '1ère op. - Majoration situation début'),
        ('first_decrease', '1ère op. - Diminution situation début'),
        # DNA détaillées
        ('dna_car', 'DNA - Frais de voiture'),
        ('dna_car_co2', 'DNA - Frais voiture (formule CO2)'),
        ('dna_fuel_card', 'DNA - Cartes carburant'),
        ('dna_restaurant', 'DNA - Frais de restaurant (31%)'),
        ('dna_reception', 'DNA - Frais de réception (50%)'),
        ('dna_gift', 'DNA - Cadeaux d\'affaires (50%)'),
        ('dna_gift_full', 'DNA - Cadeaux > 125€ (100%)'),
        ('dna_clothing', 'DNA - Vêtements professionnels'),
        ('dna_fine', 'DNA - Amendes et pénalités'),
        ('dna_tax_fine', 'DNA - Accroissements d\'impôt'),
        ('dna_late_interest', 'DNA - Intérêts de retard fiscaux'),
        ('dna_pension_excess', 'DNA - Pensions excessives'),
        ('dna_pension_80', 'DNA - Cotisations > limite 80%'),
        ('dna_director_fee', 'DNA - Tantièmes'),
        ('dna_secret_commission', 'DNA - Commissions secrètes'),
        ('dna_provision', 'DNA - Provisions non admises'),
        ('dna_depreciation', 'DNA - Amortissements excédentaires'),
        ('dna_interest_thin_cap', 'DNA - Intérêts sous-capitalisation'),
        ('dna_interest_transfer', 'DNA - Intérêts prix de transfert'),
        ('dna_regional_tax', 'DNA - Impôts régionaux'),
        ('dna_isoc', 'DNA - ISOC et impôts étrangers similaires'),
        ('dna_other', 'DNA - Autres dépenses non admises'),
        # Provisions
        ('provision_excess', 'Provisions excédentaires'),
        ('provision_used', 'Reprises de provisions utilisées'),
        ('provision_taxed', 'Provisions antérieurement taxées'),
        # Amortissements
        ('depreciation_excess', 'Amortissements excédentaires'),
        ('depreciation_recovery', 'Reprises d\'amortissements'),
        ('depreciation_spread', 'Amortissements sur plus-values'),
        # Plus-values
        ('capital_gain_normal', 'Plus-value - Taxation normale'),
        ('capital_gain_spread', 'Plus-value - Taxation étalée'),
        ('capital_gain_exempt', 'Plus-value - Immunisée'),
        ('capital_gain_shares', 'Plus-value sur actions'),
        ('capital_gain_reinvest', 'Plus-value réinvestie'),
        # Moins-values
        ('capital_loss_normal', 'Moins-value déductible'),
        ('capital_loss_shares', 'Moins-value actions (non déd.)'),
        # Déductions
        ('ded_rdt', 'Déduction RDT'),
        ('ded_rdt_excess', 'RDT excédentaire reporté'),
        ('ded_innovation', 'Déduction innovation (85%)'),
        ('ded_patent', 'Déduction revenus brevets'),
        ('ded_investment', 'Déduction pour investissement'),
        ('ded_investment_spread', 'Déd. investissement étalée'),
        ('ded_nid', 'Intérêts notionnels (NID/DIN)'),
        ('ded_donation', 'Libéralités déductibles'),
        ('ded_loss', 'Pertes antérieures'),
        ('ded_loss_foreign', 'Pertes établissement étranger'),
        # Exonérations
        ('exempt_subsidy', 'Subsides en capital'),
        ('exempt_regional', 'Exonération régionale'),
        ('exempt_other', 'Autres exonérations'),
        # Réserves
        ('reserve_legal', 'Dotation réserve légale'),
        ('reserve_available', 'Mouvement réserves disponibles'),
        ('reserve_unavailable', 'Mouvement réserves indisponibles'),
        # Précomptes
        ('prepayment', 'Précompte mobilier'),
        ('prepayment_foreign', 'Précompte étranger'),
        ('withholding', 'Retenue à la source'),
        # Autres
        ('other_increase', 'Autre majoration'),
        ('other_decrease', 'Autre diminution'),
    ], string='Catégorie', required=True, default='dna_other')

    movement_type = fields.Selection([
        ('increase', 'Majoration (+)'),
        ('decrease', 'Diminution (-)'),
    ], string='Type', required=True, default='increase',
       compute='_compute_movement_type', store=True, readonly=False)

    # === MONTANTS ===
    accounting_amount = fields.Monetary(
        string='Montant comptable',
        currency_field='currency_id',
        help="Montant inscrit en comptabilité",
    )
    fiscal_amount = fields.Monetary(
        string='Montant fiscal',
        currency_field='currency_id',
        help="Montant retenu fiscalement",
    )
    adjustment_amount = fields.Monetary(
        string='Montant ajustement',
        currency_field='currency_id',
        compute='_compute_adjustment_amount',
        store=True,
        help="Différence entre comptable et fiscal = réintégration/déduction",
    )
    
    # === CALCULS SPÉCIFIQUES ===
    # Pour DNA véhicules
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Véhicule',
        help="Lien vers le véhicule fleet (si module installé)",
    )
    co2_emission = fields.Float(
        string='Émission CO2 (g/km)',
    )
    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Essence'),
        ('hybrid', 'Hybride'),
        ('electric', 'Électrique'),
        ('cng', 'CNG'),
        ('lpg', 'LPG'),
    ], string='Type carburant')
    dna_percentage_calculated = fields.Float(
        string='% DNA calculé',
        compute='_compute_vehicle_dna',
        store=True,
    )
    
    # Pour DNA pourcentage fixe
    dna_percentage_fixed = fields.Float(
        string='% DNA fixe',
    )
    base_amount = fields.Monetary(
        string='Base de calcul',
        currency_field='currency_id',
    )

    # Pour plus-values
    acquisition_date = fields.Date(string='Date d\'acquisition')
    disposal_date = fields.Date(string='Date de cession')
    holding_period_months = fields.Integer(
        compute='_compute_holding_period',
        string='Durée détention (mois)',
    )
    reinvestment_deadline = fields.Date(
        string='Date limite réinvestissement',
        help="Pour taxation étalée des plus-values",
    )
    reinvestment_amount = fields.Monetary(
        string='Montant réinvesti',
        currency_field='currency_id',
    )

    # Pour RDT
    participation_percentage = fields.Float(
        string='% de participation',
        help="Pourcentage de détention pour RDT",
    )
    participation_value = fields.Monetary(
        string='Valeur participation',
        currency_field='currency_id',
    )
    rdt_eligible = fields.Boolean(
        string='Éligible RDT',
        compute='_compute_rdt_eligibility',
    )

    # Pour NID
    risk_capital_base = fields.Monetary(
        string='Capital à risque',
        currency_field='currency_id',
    )
    nid_rate = fields.Float(
        string='Taux NID (%)',
    )

    # Pour pertes
    loss_year = fields.Integer(string='Année de la perte')
    loss_original_amount = fields.Monetary(
        string='Perte originale',
        currency_field='currency_id',
    )
    loss_used_amount = fields.Monetary(
        string='Perte utilisée',
        currency_field='currency_id',
    )
    loss_remaining = fields.Monetary(
        string='Perte restante',
        currency_field='currency_id',
        compute='_compute_loss_remaining',
        store=True,
    )

    # === LIENS COMPTABLES ===
    account_ids = fields.Many2many(
        'account.account',
        string='Comptes comptables',
    )
    move_line_ids = fields.Many2many(
        'account.move.line',
        string='Écritures comptables',
    )
    asset_id = fields.Many2one(
        'account.asset',
        string='Immobilisation',
        help="Lien vers l'immobilisation (si module account_asset installé)",
    )

    # === CODES FISCAUX ===
    tax_code_id = fields.Many2one(
        'biztax.tax.code',
        string='Code fiscal',
    )
    xbrl_element = fields.Char(
        related='tax_code_id.xbrl_element',
        string='Élément XBRL',
    )

    # === ANNEXES ===
    requires_annex = fields.Boolean(
        string='Annexe requise',
        compute='_compute_requires_annex',
    )
    annex_type = fields.Char(
        string='Type annexe',
        compute='_compute_requires_annex',
    )

    # === DOCUMENTATION ===
    legal_reference = fields.Char(string='Base légale')
    notes = fields.Text(string='Notes / Justification')
    auto_calculated = fields.Boolean(
        string='Calculé automatiquement',
        default=False,
    )

    @api.depends('category')
    def _compute_movement_type(self):
        """Determine movement type based on category"""
        decrease_categories = [
            'first_decrease', 'ded_rdt', 'ded_rdt_excess', 'ded_innovation',
            'ded_patent', 'ded_investment', 'ded_investment_spread', 'ded_nid',
            'ded_donation', 'ded_loss', 'ded_loss_foreign', 'exempt_subsidy',
            'exempt_regional', 'exempt_other', 'provision_taxed',
            'capital_gain_exempt', 'capital_gain_spread', 'other_decrease',
        ]
        for rec in self:
            if rec.category in decrease_categories:
                rec.movement_type = 'decrease'
            else:
                rec.movement_type = 'increase'

    @api.depends('accounting_amount', 'fiscal_amount', 'base_amount', 
                 'dna_percentage_fixed', 'dna_percentage_calculated')
    def _compute_adjustment_amount(self):
        """Calculate the fiscal adjustment amount"""
        for rec in self:
            if rec.accounting_amount and rec.fiscal_amount:
                # Différence entre comptable et fiscal
                rec.adjustment_amount = abs(rec.accounting_amount - rec.fiscal_amount)
            elif rec.base_amount and (rec.dna_percentage_fixed or rec.dna_percentage_calculated):
                # Calcul sur base avec pourcentage
                pct = rec.dna_percentage_fixed or rec.dna_percentage_calculated
                rec.adjustment_amount = rec.base_amount * (pct / 100)
            elif rec.accounting_amount:
                rec.adjustment_amount = rec.accounting_amount
            else:
                rec.adjustment_amount = 0

    @api.depends('co2_emission', 'fuel_type')
    def _compute_vehicle_dna(self):
        """
        Calculate DNA percentage for vehicles based on CO2 emission.
        Formula (Art. 66 CIR92):
        - Diesel: 120% - (0.5% × CO2 coefficient × CO2)
        - Petrol: 120% - (0.5% × CO2 coefficient × CO2)  
        - Electric: 0% DNA (100% deductible up to 2026)
        
        Minimum 50%, Maximum 100% for non-electric
        """
        for rec in self:
            if rec.fuel_type == 'electric':
                rec.dna_percentage_calculated = 0
            elif rec.co2_emission:
                # Formula: DNA% = 120 - (0.5 * coef * CO2)
                # Coefficient varies by fuel type
                if rec.fuel_type == 'diesel':
                    coef = 1.0
                else:
                    coef = 0.95  # Petrol, hybrid, etc.
                
                deductible_pct = 120 - (0.5 * coef * rec.co2_emission)
                deductible_pct = max(50, min(100, deductible_pct))
                rec.dna_percentage_calculated = 100 - deductible_pct
            else:
                # Default: 40% DNA (60% deductible) as fallback
                rec.dna_percentage_calculated = 40

    @api.depends('acquisition_date', 'disposal_date')
    def _compute_holding_period(self):
        for rec in self:
            if rec.acquisition_date and rec.disposal_date:
                delta = relativedelta(rec.disposal_date, rec.acquisition_date)
                rec.holding_period_months = delta.years * 12 + delta.months
            else:
                rec.holding_period_months = 0

    @api.depends('participation_percentage', 'participation_value', 
                 'holding_period_months')
    def _compute_rdt_eligibility(self):
        """
        Check RDT eligibility (Art. 202-204 CIR92):
        - Participation >= 10% OR acquisition value >= 2.5M EUR
        - Holding period >= 12 months
        - Conditions on distributing company
        """
        for rec in self:
            value_condition = (rec.participation_value or 0) >= 2500000
            percentage_condition = (rec.participation_percentage or 0) >= 10
            holding_condition = (rec.holding_period_months or 0) >= 12
            
            rec.rdt_eligible = (value_condition or percentage_condition) and holding_condition

    @api.depends('loss_original_amount', 'loss_used_amount')
    def _compute_loss_remaining(self):
        for rec in self:
            rec.loss_remaining = (rec.loss_original_amount or 0) - (rec.loss_used_amount or 0)

    @api.depends('category')
    def _compute_requires_annex(self):
        """Determine if an annex is required based on category"""
        annex_mapping = {
            'dna_car': '275F',
            'dna_car_co2': '275F',
            'dna_fuel_card': '275F',
            'dna_provision': '275C',
            'provision_excess': '275C',
            'capital_gain_spread': '275U',
            'capital_gain_exempt': '275U',
            'capital_gain_shares': '275U',
            'ded_investment': '275K',
            'ded_investment_spread': '275K',
            'ded_nid': '275N',
            'ded_loss': '275P',
            'ded_loss_foreign': '275P',
            'ded_innovation': '275W',
            'dna_secret_commission': '328S',
        }
        for rec in self:
            if rec.category in annex_mapping:
                rec.requires_annex = True
                rec.annex_type = annex_mapping[rec.category]
            else:
                rec.requires_annex = False
                rec.annex_type = False


class BiztaxLossCarryforward(models.Model):
    """
    Track tax losses for carryforward with Belgian basket rules.
    Since 2018: Max deduction = 1M EUR + 70% of exceeding profit
    """
    _name = 'biztax.loss.carryforward'
    _description = 'Pertes fiscales reportables'
    _order = 'loss_year'

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
    )
    
    loss_year = fields.Integer(
        string='Exercice de la perte',
        required=True,
    )
    original_amount = fields.Monetary(
        string='Perte originale',
        currency_field='currency_id',
        required=True,
    )
    used_amount = fields.Monetary(
        string='Montant utilisé',
        currency_field='currency_id',
        default=0,
    )
    remaining_amount = fields.Monetary(
        string='Solde reportable',
        currency_field='currency_id',
        compute='_compute_remaining',
        store=True,
    )
    
    usage_ids = fields.One2many(
        'biztax.loss.usage',
        'loss_id',
        string='Utilisations',
    )
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.depends('original_amount', 'used_amount')
    def _compute_remaining(self):
        for rec in self:
            rec.remaining_amount = rec.original_amount - rec.used_amount

    def calculate_max_deduction(self, taxable_profit):
        """
        Calculate maximum loss deduction based on Belgian basket rule (Art. 206 CIR92):
        Max = 1,000,000 EUR + 70% of (profit - 1,000,000)
        """
        if taxable_profit <= 1000000:
            return taxable_profit
        else:
            return 1000000 + (0.70 * (taxable_profit - 1000000))


class BiztaxLossUsage(models.Model):
    """Track usage of carried forward losses per declaration"""
    _name = 'biztax.loss.usage'
    _description = 'Utilisation de perte reportée'

    loss_id = fields.Many2one(
        'biztax.loss.carryforward',
        string='Perte reportée',
        required=True,
        ondelete='cascade',
    )
    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
        ondelete='cascade',
    )
    amount = fields.Monetary(
        string='Montant utilisé',
        currency_field='currency_id',
        required=True,
    )
    currency_id = fields.Many2one(
        related='loss_id.currency_id',
    )


class BiztaxNIDCalculation(models.Model):
    """
    Notional Interest Deduction (NID/DIN) calculation.
    Based on 10-year OLO rate with adjustments.
    """
    _name = 'biztax.nid.calculation'
    _description = 'Calcul intérêts notionnels (NID)'
    
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

    # Risk Capital Components
    equity_start = fields.Monetary(
        string='Fonds propres début',
        currency_field='currency_id',
    )
    equity_end = fields.Monetary(
        string='Fonds propres fin',
        currency_field='currency_id',
    )
    average_equity = fields.Monetary(
        string='Fonds propres moyens',
        currency_field='currency_id',
        compute='_compute_risk_capital',
        store=True,
    )
    
    # Deductions from risk capital (Art. 205ter CIR92)
    own_shares = fields.Monetary(
        string='Actions propres',
        currency_field='currency_id',
    )
    financial_fixed_assets = fields.Monetary(
        string='Immobilisations financières (participations)',
        currency_field='currency_id',
    )
    foreign_establishments = fields.Monetary(
        string='Établissements étrangers',
        currency_field='currency_id',
    )
    real_estate_excess = fields.Monetary(
        string='Immeubles non affectés',
        currency_field='currency_id',
    )
    revaluation_surplus = fields.Monetary(
        string='Plus-values de réévaluation',
        currency_field='currency_id',
    )
    subsidies = fields.Monetary(
        string='Subsides en capital',
        currency_field='currency_id',
    )
    
    risk_capital = fields.Monetary(
        string='Capital à risque',
        currency_field='currency_id',
        compute='_compute_risk_capital',
        store=True,
    )
    
    # NID Rate
    nid_rate_base = fields.Float(
        string='Taux de base (%)',
        help="Taux OLO 10 ans de l'avant-dernière année",
    )
    nid_rate_sme_bonus = fields.Float(
        string='Bonus PME (%)',
        default=0.5,
    )
    nid_rate_applied = fields.Float(
        string='Taux appliqué (%)',
        compute='_compute_nid_rate',
        store=True,
    )
    
    # Result
    nid_amount = fields.Monetary(
        string='Déduction NID',
        currency_field='currency_id',
        compute='_compute_nid_amount',
        store=True,
    )

    @api.depends('equity_start', 'equity_end', 'own_shares', 'financial_fixed_assets',
                 'foreign_establishments', 'real_estate_excess', 'revaluation_surplus', 'subsidies')
    def _compute_risk_capital(self):
        for rec in self:
            rec.average_equity = (rec.equity_start + rec.equity_end) / 2
            
            deductions = (
                rec.own_shares +
                rec.financial_fixed_assets +
                rec.foreign_establishments +
                rec.real_estate_excess +
                rec.revaluation_surplus +
                rec.subsidies
            )
            
            rec.risk_capital = max(0, rec.average_equity - deductions)

    @api.depends('nid_rate_base', 'nid_rate_sme_bonus', 'declaration_id.is_sme')
    def _compute_nid_rate(self):
        for rec in self:
            base_rate = rec.nid_rate_base or 0
            if rec.declaration_id.is_sme:
                rec.nid_rate_applied = base_rate + rec.nid_rate_sme_bonus
            else:
                rec.nid_rate_applied = base_rate
            # Cap at 3% maximum
            rec.nid_rate_applied = min(3.0, rec.nid_rate_applied)

    @api.depends('risk_capital', 'nid_rate_applied')
    def _compute_nid_amount(self):
        for rec in self:
            rec.nid_amount = rec.risk_capital * (rec.nid_rate_applied / 100)
