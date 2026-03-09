# -*- coding: utf-8 -*-
from odoo import models, api, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoice_cash_rounding_id = fields.Many2one(
        'account.cash.rounding',
        string='Arrondi des espèces',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'invoice_cash_rounding_id' in fields_list and not res.get('invoice_cash_rounding_id'):
            rounding = self.env['account.cash.rounding'].search([
                ('name', 'ilike', 'Arrondi Euro')
            ], limit=1)
            if rounding:
                res['invoice_cash_rounding_id'] = rounding.id
        return res

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if not invoice_vals.get('invoice_cash_rounding_id') and self.invoice_cash_rounding_id:
            invoice_vals['invoice_cash_rounding_id'] = self.invoice_cash_rounding_id.id
        return invoice_vals
