# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BiztaxAdjustment(models.Model):
    _name = 'biztax.adjustment'
    _description = 'Ajustement fiscal Biztax'
    _order = 'category, sequence, id'

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
    
    # Code fiscal be-tax
    tax_code_id = fields.Many2one(
        'biztax.tax.code',
        string='Code fiscal',
        required=True,
        domain="[('declaration_type', '=', parent.declaration_type)]",
    )
    tax_code = fields.Char(
        related='tax_code_id.code',
        store=True,
    )
    
    name = fields.Char(
        string='Description',
        required=True,
    )
    
    category = fields.Selection([
        ('dna', 'Dépenses Non Admises (DNA)'),
        ('reserve', 'Mouvement de réserves'),
        ('provision', 'Provisions'),
        ('depreciation', 'Amortissements'),
        ('plus_value', 'Plus-values'),
        ('deduction', 'Déductions'),
        ('exemption', 'Exonérations'),
        ('loss_carryforward', 'Pertes antérieures'),
        ('rdi', 'Revenus définitivement imposés (RDI)'),
        ('innovation', 'Déduction pour innovation'),
        ('investment', "Déduction pour investissement"),
        ('other', 'Autres'),
    ], string='Catégorie', required=True, default='dna')
    
    adjustment_type = fields.Selection([
        ('increase', 'Majoration'),
        ('decrease', 'Diminution'),
    ], string='Type', required=True, default='increase')
    
    amount = fields.Monetary(
        string='Montant',
        required=True,
        currency_field='currency_id',
    )
    
    # Pour les DNA avec pourcentage
    base_amount = fields.Monetary(
        string='Montant de base',
        currency_field='currency_id',
        help="Montant comptable de base avant application du pourcentage DNA",
    )
    dna_percentage = fields.Float(
        string='% DNA',
        help="Pourcentage de dépense non admise",
    )
    
    # Détails
    account_id = fields.Many2one(
        'account.account',
        string='Compte comptable',
        domain="[('company_id', '=', company_id)]",
    )
    move_line_ids = fields.Many2many(
        'account.move.line',
        string='Écritures liées',
    )
    
    notes = fields.Text(string='Notes / Justification')
    
    # Import automatique
    auto_imported = fields.Boolean(
        string='Importé automatiquement',
        default=False,
    )
    
    # XBRL
    xbrl_element = fields.Char(
        related='tax_code_id.xbrl_element',
        string='Élément XBRL',
    )

    @api.onchange('tax_code_id')
    def _onchange_tax_code(self):
        if self.tax_code_id:
            self.name = self.tax_code_id.name
            if self.tax_code_id.default_category:
                self.category = self.tax_code_id.default_category
            if self.tax_code_id.default_adjustment_type:
                self.adjustment_type = self.tax_code_id.default_adjustment_type

    @api.onchange('base_amount', 'dna_percentage')
    def _onchange_dna_calculation(self):
        if self.base_amount and self.dna_percentage:
            self.amount = self.base_amount * (self.dna_percentage / 100)

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_("Le montant doit être positif."))


class BiztaxAdjustmentTemplate(models.Model):
    """Templates for common fiscal adjustments"""
    _name = 'biztax.adjustment.template'
    _description = 'Modèle d\'ajustement fiscal'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    tax_code_id = fields.Many2one(
        'biztax.tax.code',
        string='Code fiscal',
        required=True,
    )
    category = fields.Selection([
        ('dna', 'Dépenses Non Admises (DNA)'),
        ('reserve', 'Mouvement de réserves'),
        ('provision', 'Provisions'),
        ('depreciation', 'Amortissements'),
        ('plus_value', 'Plus-values'),
        ('deduction', 'Déductions'),
        ('exemption', 'Exonérations'),
        ('loss_carryforward', 'Pertes antérieures'),
        ('rdi', 'Revenus définitivement imposés (RDI)'),
        ('innovation', 'Déduction pour innovation'),
        ('investment', "Déduction pour investissement"),
        ('other', 'Autres'),
    ], string='Catégorie', required=True)
    
    adjustment_type = fields.Selection([
        ('increase', 'Majoration'),
        ('decrease', 'Diminution'),
    ], string='Type', required=True)
    
    default_dna_percentage = fields.Float(
        string='% DNA par défaut',
    )
    
    description = fields.Text(string='Description')
    legal_reference = fields.Char(string='Référence légale')

    def action_create_adjustment(self, declaration):
        """Create an adjustment from this template"""
        return self.env['biztax.adjustment'].create({
            'declaration_id': declaration.id,
            'tax_code_id': self.tax_code_id.id,
            'name': self.name,
            'category': self.category,
            'adjustment_type': self.adjustment_type,
            'dna_percentage': self.default_dna_percentage,
            'amount': 0,
        })
