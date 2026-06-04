# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_important_internal_note = fields.Boolean(
        string='Note interne importante',
        compute='_compute_has_important_internal_note',
    )

    @api.depends('internal_note')
    def _compute_has_important_internal_note(self):
        for order in self:
            order.has_important_internal_note = self._note_is_significant(order.internal_note)

    @staticmethod
    def _note_is_significant(html_value):
        if not html_value:
            return False
        text = re.sub(r'<[^>]+>', '', html_value)
        text = text.replace('&nbsp;', ' ').strip()
        return bool(text)
