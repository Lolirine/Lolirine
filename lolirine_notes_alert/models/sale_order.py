# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_important_internal_note = fields.Boolean(
        string='Note interne importante',
        compute='_compute_has_important_internal_note',
    )

    @api.depends('internal_note', 'website_id')
    def _compute_has_important_internal_note(self):
        for order in self:
            # l'alerte concerne les abonnements du garde-meuble : pas les devis
            # et commandes du Pool Store (devis piscine PSC/, commandes POOL-)
            pool = (getattr(order, 'is_pool_quote', False) or getattr(order, 'is_dropship_order', False)
                    or (order.website_id and order.website_id.id == 6))
            order.has_important_internal_note = not pool and self._note_is_significant(order.internal_note)

    @staticmethod
    def _note_is_significant(html_value):
        if not html_value:
            return False
        text = re.sub(r'<[^>]+>', '', html_value)
        text = text.replace('&nbsp;', ' ').strip()
        return bool(text)
