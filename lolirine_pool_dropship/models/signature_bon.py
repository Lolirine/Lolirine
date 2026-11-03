# -*- coding: utf-8 -*-
"""Signature en ligne du bon de commande fournisseur (dessinée dans Odoo), imprimée sur le PDF."""
from odoo import fields, models


class PurchaseOrderSignature(models.Model):
    _inherit = 'purchase.order'

    pool_signature = fields.Image("Signature", max_width=1024, max_height=1024, copy=False, attachment=True)
    pool_signe_par = fields.Char("Signé par", copy=False)
    pool_signe_le = fields.Datetime("Signé le", copy=False, readonly=True)

    def write(self, vals):
        if 'pool_signature' in vals:
            if vals.get('pool_signature'):
                vals.setdefault('pool_signe_le', fields.Datetime.now())
                if not vals.get('pool_signe_par'):
                    vals['pool_signe_par'] = self.env.user.name
            else:
                vals.update(pool_signe_le=False, pool_signe_par=False)
        return super().write(vals)
