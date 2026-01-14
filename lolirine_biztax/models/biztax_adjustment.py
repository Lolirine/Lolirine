# -*- coding: utf-8 -*-
"""
Biztax Adjustment Model - Fiscal adjustments for Belgian tax declarations
Handles DNA (Dépenses Non Admises), deductions, provisions, etc.

IMPORTANT Odoo 19: Le champ company_id n'existe plus sur account.account
Le domaine sur account_id ne doit pas utiliser company_id
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiztaxAdjustment(models.Model):
    """
    Fiscal adjustment for Biztax declaration.
    Manages increases and decreases to the taxable base.
    """
    _name = 'biztax.adjustment'
    _description = 'Ajustement fiscal Biztax'
    _order = 'sequence, id'
    _rec_name = 'name'

    # -------------------------------------------------------------------------
    # BASIC FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Description',
        required=True,
        tracking=True,
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10,
    )
    
    declaration_id = fields.Many2one(
        'biztax.declaration',
        string='Déclaration',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    # -------------------------------------------------------------------------
    # ACCOUNTING FIELDS - SANS DOMAINE company_id (n'existe plus en Odoo 19)
    # -------------------------------------------------------------------------
    account_id = fields.Many2one(
        'account.account',
        string='Compte comptable',
        help="Compte comptable lié à cet ajustement (optionnel)",
        # IMPORTANT: Pas de domain sur company_id car ce champ n'existe plus
        # sur account.account dans Odoo 19
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='declaration_id.currency_id',
        store=True,
        readonly=True,
    )
    
    tax_code_id = fields.Many2one(
        'biztax.tax.code',
        string='Code fiscal XBRL',
        help="Code de la taxonomie be-tax correspondant",
    )
    
    move_line_ids = fields.Many2many(
        'account.move.line',
        'biztax_adjustment_move_line_rel',
        'adjustment_id',
        'move_line_id',
        string='Écritures comptables',
        help="Lignes comptables liées à cet ajustement",
    )
    
    # -------------------------------------------------------------------------
    # CLASSIFICATION FIELDS
    # -------------------------------------------------------------------------
    category = fields.Selection([
        ('dna', 'Dépenses Non Admises (DNA)'),
        ('dna_vehicle', 'DNA Véhicules'),
        ('dna_restaurant', 'DNA Frais de restaurant'),
        ('dna_reception', 'DNA Frais de réception'),
        ('dna_gifts', 'DNA Cadeaux d\'affaires'),
        ('dna_fines', 'DNA Amendes et pénalités'),
        ('dna_interest', 'DNA Intérêts excédentaires'),
        ('provision', 'Provisions non déductibles'),
        ('depreciation', 'Amortissements non admis'),
        ('plus_value', 'Plus-values'),
        ('plus_value_spread', 'Plus-values étalées'),
        ('plus_value_exempt', 'Plus-values immunisées'),
        ('rdt', 'Revenus Définitivement Taxés (RDT)'),
        ('innovation', 'Déduction pour innovation'),
        ('investment', 'Déduction pour investissement'),
        ('nid', 'Déduction intérêts notionnels (NID)'),
        ('loss_carryforward', 'Report de pertes'),
        ('other_increase', 'Autre majoration'),
        ('other_decrease', 'Autre diminution'),
    ], string='Catégorie', default='dna', required=True, tracking=True)
    
    adjustment_type = fields.Selection([
        ('increase', 'Majoration (réintégration)'),
        ('decrease', 'Diminution (déduction)'),
    ], string='Type d\'ajustement', required=True, default='increase', tracking=True)
    
    # -------------------------------------------------------------------------
    # AMOUNT FIELDS
    # -------------------------------------------------------------------------
    amount = fields.Monetary(
        string='Montant',
        currency_field='currency_id',
        required=True,
        tracking=True,
    )
    
    base_amount = fields.Monetary(
        string='Montant de base',
        currency_field='currency_id',
        help="Montant comptable avant application du pourcentage DNA",
    )
    
    dna_percentage = fields.Float(
        string='Pourcentage DNA',
        default=100.0,
        help="Pourcentage de la dépense non admise fiscalement",
    )
    
    signed_amount = fields.Monetary(
        string='Montant signé',
        currency_field='currency_id',
        compute='_compute_signed_amount',
        store=True,
        help="Montant positif pour majorations, négatif pour diminutions",
    )
    
    # -------------------------------------------------------------------------
    # VEHICLE-SPECIFIC FIELDS (for DNA vehicles)
    # -------------------------------------------------------------------------
    vehicle_co2 = fields.Integer(
        string='Émissions CO2 (g/km)',
        help="Pour calcul automatique DNA véhicule selon Art. 66 CIR92",
    )
    
    vehicle_fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Essence'),
        ('electric', 'Électrique'),
        ('hybrid_diesel', 'Hybride diesel'),
        ('hybrid_petrol', 'Hybride essence'),
        ('cng', 'CNG/LPG'),
    ], string='Type de carburant')
    
    vehicle_deduction_rate = fields.Float(
        string='Taux de déduction véhicule (%)',
        compute='_compute_vehicle_deduction_rate',
        store=True,
        help="Taux calculé selon émissions CO2 et type de carburant",
    )
    
    # -------------------------------------------------------------------------
    # DOCUMENTATION FIELDS
    # -------------------------------------------------------------------------
    legal_reference = fields.Char(
        string='Base légale',
        help="Article CIR92 ou référence légale",
    )
    
    notes = fields.Text(
        string='Notes',
        help="Détails et justification de l'ajustement",
    )
    
    # -------------------------------------------------------------------------
    # COMPUTED FIELDS
    # -------------------------------------------------------------------------
    @api.depends('amount', 'adjustment_type')
    def _compute_signed_amount(self):
        for record in self:
            if record.adjustment_type == 'decrease':
                record.signed_amount = -abs(record.amount)
            else:
                record.signed_amount = abs(record.amount)
    
    @api.depends('vehicle_co2', 'vehicle_fuel_type')
    def _compute_vehicle_deduction_rate(self):
        """
        Calcul du taux de déduction véhicule selon Art. 66 CIR92
        Formule 2024+: 120% - (0.5% × CO2) pour diesel
                       120% - (0.5% × CO2 × 0.95) pour essence
        Minimum 50%, Maximum 100%
        Électrique: 100%
        """
        for record in self:
            if not record.vehicle_co2 or not record.vehicle_fuel_type:
                record.vehicle_deduction_rate = 0
                continue
                
            if record.vehicle_fuel_type == 'electric':
                record.vehicle_deduction_rate = 100
            elif record.vehicle_fuel_type in ('diesel', 'hybrid_diesel'):
                rate = 120 - (0.5 * record.vehicle_co2)
                record.vehicle_deduction_rate = max(50, min(100, rate))
            else:  # essence, hybrid_petrol, cng
                rate = 120 - (0.5 * record.vehicle_co2 * 0.95)
                record.vehicle_deduction_rate = max(50, min(100, rate))
    
    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('category')
    def _onchange_category(self):
        """Set adjustment_type based on category"""
        decrease_categories = [
            'rdt', 'innovation', 'investment', 'nid', 
            'loss_carryforward', 'plus_value_exempt',
            'other_decrease'
        ]
        if self.category in decrease_categories:
            self.adjustment_type = 'decrease'
        elif self.category and self.category != 'other_decrease':
            self.adjustment_type = 'increase'
    
    @api.onchange('base_amount', 'dna_percentage')
    def _onchange_base_amount(self):
        """Calculate amount from base_amount and percentage"""
        if self.base_amount and self.dna_percentage:
            self.amount = self.base_amount * (self.dna_percentage / 100)
    
    @api.onchange('vehicle_co2', 'vehicle_fuel_type', 'base_amount')
    def _onchange_vehicle_fields(self):
        """Auto-calculate DNA for vehicles"""
        if self.category == 'dna_vehicle' and self.base_amount:
            if self.vehicle_deduction_rate:
                self.dna_percentage = 100 - self.vehicle_deduction_rate
                self.amount = self.base_amount * (self.dna_percentage / 100)
    
    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_(
                    "Le montant doit être positif. "
                    "Utilisez le type d'ajustement pour indiquer s'il s'agit "
                    "d'une majoration ou d'une diminution."
                ))
    
    @api.constrains('dna_percentage')
    def _check_dna_percentage(self):
        for record in self:
            if record.dna_percentage < 0 or record.dna_percentage > 100:
                raise ValidationError(_(
                    "Le pourcentage DNA doit être entre 0 et 100."
                ))
