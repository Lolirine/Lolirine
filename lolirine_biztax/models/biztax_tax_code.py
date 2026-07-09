# -*- coding: utf-8 -*-
"""
Biztax Tax Code Model - XBRL taxonomy elements mapping
"""
from odoo import api, fields, models, _


class BiztaxTaxCode(models.Model):
    """
    XBRL tax code from be-tax taxonomy.
    Maps fiscal concepts to XBRL elements.
    """
    _name = 'biztax.tax.code'
    _description = 'Code fiscal XBRL Biztax'
    _order = 'code'
    _rec_name = 'display_name'

    code = fields.Char(
        string='Code',
        required=True,
        index=True,
    )
    
    name = fields.Char(
        string='Libellé',
        required=True,
        translate=True,
    )
    
    display_name = fields.Char(
        string='Nom complet',
        compute='_compute_display_name',
        store=True,
    )
    
    xbrl_element = fields.Char(
        string='Élément XBRL',
        help="Nom de l'élément dans la taxonomie be-tax",
    )
    
    section = fields.Selection([
        ('i', 'I. Bénéfice réservé'),
        ('ii', 'II. Situation de début'),
        ('iii', 'III. Majorations'),
        ('iv', 'IV. Diminutions'),
        ('a', 'A. Détermination base imposable'),
        ('b', 'B. Ventilation résultat'),
        ('c', 'C. Déductions'),
        ('d', 'D. Cotisations distinctes'),
        ('j', 'J. Pertes'),
    ], string='Section', required=True, default='iii')
    
    description = fields.Text(
        string='Description',
        translate=True,
    )
    
    legal_reference = fields.Char(
        string='Base légale',
        help="Article CIR92 ou autre référence",
    )
    
    active = fields.Boolean(default=True)
    
    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"
    
    code_unique = models.Constraint(
        'UNIQUE(code)',
        "Le code fiscal doit être unique!",
    )
