# -*- coding: utf-8 -*-
from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_rounding(self):
        return self.env['account.cash.rounding'].search([
            ('name', 'ilike', 'Arrondi Euro')
        ], limit=1)

    @api.model
    def default_get(self, fields_list):
        """Applique l'arrondi Euro par défaut sur les nouveaux devis"""
        res = super().default_get(fields_list)
        if 'invoice_cash_rounding_id' in fields_list and not res.get('invoice_cash_rounding_id'):
            rounding = self._get_rounding()
            if rounding:
                res['invoice_cash_rounding_id'] = rounding.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Garantit l'arrondi sur la création (abonnements automatiques)"""
        rounding = self._get_rounding()
        for vals in vals_list:
            if rounding and not vals.get('invoice_cash_rounding_id'):
                vals['invoice_cash_rounding_id'] = rounding.id
        return super().create(vals_list)

    def _prepare_invoice(self):
        """Garantit l'arrondi sur les factures générées depuis les devis"""
        invoice_vals = super()._prepare_invoice()
        if not invoice_vals.get('invoice_cash_rounding_id'):
            rounding = self._get_rounding()
            if rounding:
                invoice_vals['invoice_cash_rounding_id'] = rounding.id
        return invoice_vals
