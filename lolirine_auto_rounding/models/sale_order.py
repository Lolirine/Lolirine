# -*- coding: utf-8 -*-
from odoo import models, api, fields
import math


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

    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id',
                 'payment_term_id', 'invoice_cash_rounding_id')
    def _compute_amounts(self):
        super()._compute_amounts()
        for order in self:
            if not order.invoice_cash_rounding_id:
                continue
            rounding = order.invoice_cash_rounding_id.rounding  # ex: 1.0
            method = order.invoice_cash_rounding_id.rounding_method  # UP/DOWN/HALF_UP
            total = order.amount_total

            if method == 'UP':
                rounded = math.ceil(total / rounding) * rounding
            elif method == 'DOWN':
                rounded = math.floor(total / rounding) * rounding
            else:  # HALF_UP
                rounded = round(total / rounding) * rounding

            rounded = order.currency_id.round(rounded)
            diff = rounded - total

            order.amount_total = rounded
            order.amount_tax = order.currency_id.round(order.amount_tax + diff)

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if not invoice_vals.get('invoice_cash_rounding_id') and self.invoice_cash_rounding_id:
            invoice_vals['invoice_cash_rounding_id'] = self.invoice_cash_rounding_id.id
        return invoice_vals
