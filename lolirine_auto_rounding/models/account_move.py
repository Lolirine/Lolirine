# -*- coding: utf-8 -*-
from odoo import models, api, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_default_cash_rounding(self):
        """Récupère l'arrondi Euro par défaut"""
        rounding = self.env['account.cash.rounding'].search([
            ('name', 'ilike', 'Arrondi Euro')
        ], limit=1)
        return rounding.id if rounding else False

    invoice_cash_rounding_id = fields.Many2one(
        default=_get_default_cash_rounding
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Applique automatiquement l'arrondi sur les factures clients"""
        for vals in vals_list:
            move_type = vals.get('move_type', self.env.context.get('default_move_type', 'entry'))
            if move_type in ('out_invoice', 'out_refund') and not vals.get('invoice_cash_rounding_id'):
                rounding = self.env['account.cash.rounding'].search([
                    ('name', 'ilike', 'Arrondi Euro')
                ], limit=1)
                if rounding:
                    vals['invoice_cash_rounding_id'] = rounding.id
        return super().create(vals_list)
