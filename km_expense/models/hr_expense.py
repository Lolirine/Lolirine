# -*- coding: utf-8 -*-

from odoo import models, fields


class HrExpense(models.Model):
    """Extension des notes de frais pour les indemnités kilométriques"""
    _inherit = 'hr.expense'

    km_trajet_id = fields.Many2one(
        'km.trajet',
        string='Trajet associé',
        readonly=True,
    )
    
    est_indemnite_km = fields.Boolean(
        string='Indemnité kilométrique',
        compute='_compute_est_indemnite_km',
        store=True,
    )

    def _compute_est_indemnite_km(self):
        for expense in self:
            expense.est_indemnite_km = bool(expense.km_trajet_id)
