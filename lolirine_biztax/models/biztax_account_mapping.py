# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class BiztaxAccountMapping(models.Model):
    """
    Mapping between accounting accounts and tax codes
    Used to automatically import DNA and other adjustments from accounting
    """
    _name = 'biztax.account.mapping'
    _description = 'Mapping compte comptable - code fiscal'
    _order = 'sequence, account_code_prefix'

    name = fields.Char(string='Description')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    
    # Account identification
    account_id = fields.Many2one(
        'account.account',
        string='Compte comptable',
        domain="[('company_id', '=', company_id)]",
    )
    account_code_prefix = fields.Char(
        string='Préfixe compte',
        help="Préfixe du code comptable (ex: 617 pour frais de voiture)",
    )
    
    # Tax code mapping
    tax_code_id = fields.Many2one(
        'biztax.tax.code',
        string='Code fiscal',
        required=True,
    )
    
    # DNA settings
    dna_percentage = fields.Float(
        string='% DNA',
        default=100.0,
        help="Pourcentage du montant comptable à reprendre en DNA",
    )
    
    # Category for the adjustment
    category = fields.Selection([
        ('dna', 'Dépenses Non Admises (DNA)'),
        ('deduction', 'Déductions'),
        ('other', 'Autres'),
    ], string='Catégorie', default='dna')
    
    adjustment_type = fields.Selection([
        ('increase', 'Majoration'),
        ('decrease', 'Diminution'),
    ], string='Type', default='increase')
    
    notes = fields.Text(string='Notes')

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.account_id:
            self.account_code_prefix = False
            if not self.name:
                self.name = self.account_id.name

    @api.onchange('account_code_prefix')
    def _onchange_account_code_prefix(self):
        if self.account_code_prefix:
            self.account_id = False

    @api.constrains('account_id', 'account_code_prefix')
    def _check_account_or_prefix(self):
        for record in self:
            if not record.account_id and not record.account_code_prefix:
                pass  # Allow empty for template


class BiztaxAccountMappingTemplate(models.Model):
    """
    Standard mappings for Belgian accounting
    Based on MAR (Minimum Algemeen Rekeningstelsel)
    """
    _name = 'biztax.account.mapping.template'
    _description = 'Modèle de mapping'
    _order = 'sequence, account_code_prefix'

    name = fields.Char(string='Description', required=True, translate=True)
    sequence = fields.Integer(default=10)
    
    account_code_prefix = fields.Char(
        string='Préfixe compte MAR',
        required=True,
    )
    
    tax_code_id = fields.Many2one(
        'biztax.tax.code',
        string='Code fiscal',
        required=True,
    )
    
    dna_percentage = fields.Float(
        string='% DNA standard',
        default=100.0,
    )
    
    category = fields.Selection([
        ('dna', 'Dépenses Non Admises'),
        ('deduction', 'Déductions'),
        ('other', 'Autres'),
    ], string='Catégorie', default='dna')
    
    adjustment_type = fields.Selection([
        ('increase', 'Majoration'),
        ('decrease', 'Diminution'),
    ], string='Type', default='increase')
    
    legal_reference = fields.Char(string='Référence légale')
    description = fields.Text(string='Description détaillée')

    def action_apply_to_company(self, company):
        """Create mappings for a company based on this template"""
        return self.env['biztax.account.mapping'].create({
            'name': self.name,
            'sequence': self.sequence,
            'company_id': company.id,
            'account_code_prefix': self.account_code_prefix,
            'tax_code_id': self.tax_code_id.id,
            'dna_percentage': self.dna_percentage,
            'category': self.category,
            'adjustment_type': self.adjustment_type,
        })
