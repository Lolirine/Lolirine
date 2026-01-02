# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PenaltyType(models.Model):
    _name = 'partner.penalty.type'
    _description = 'Type de pénalité'
    _order = 'category, sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    category = fields.Selection([
        ('financial', '1. Retards et manquements financiers'),
        ('rules', '2. Non-respect du règlement intérieur'),
        ('damage', '3. Dégradation ou état du box'),
        ('forbidden', '4. Usage interdit ou dangereux'),
        ('legal', '5. Frais contractuels et juridiques'),
    ], string='Catégorie', required=True, default='financial')
    
    default_amount = fields.Float(string='Montant par défaut (€)', default=0.0)
    is_percentage = fields.Boolean(string='Est un pourcentage', default=False,
                                    help="Si coché, le montant est un pourcentage")
    
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(string='Actif', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Le code doit être unique !'),
    ]
