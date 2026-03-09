# -*- coding: utf-8 -*-
from odoo import models, api, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_default_cash_rounding(self):
        rounding = self.env['account.cash.rounding'].search([
            ('name', 'ilike', 'Arrondi Euro')
        ], limit=1)
        return rounding.id if rounding else False

    invoice_cash_rounding_id = fields.Many2one(
        'account.cash.rounding',
        string='Arrondi des espèces',
        default=_get_default_cash_rounding,
    )

    @api.model_create_multi
    def create(self, vals_list):
        rounding = self.env['account.cash.rounding'].search([
            ('name', 'ilike', 'Arrondi Euro')
        ], limit=1)
        for vals in vals_list:
            if not vals.get('invoice_cash_rounding_id') and rounding:
                vals['invoice_cash_rounding_id'] = rounding.id
        return super().create(vals_list)
