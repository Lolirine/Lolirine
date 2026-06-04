# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    has_important_note = fields.Boolean(
        string='Note importante',
        compute='_compute_has_important_note',
    )

    @api.depends('comment')
    def _compute_has_important_note(self):
        """True si le champ comment contient du texte non vide (HTML stripped)."""
        for partner in self:
            partner.has_important_note = self._note_is_significant(partner.comment)

    @staticmethod
    def _note_is_significant(html_value):
        if not html_value:
            return False
        text = re.sub(r'<[^>]+>', '', html_value)
        text = text.replace('&nbsp;', ' ').strip()
        return bool(text)
