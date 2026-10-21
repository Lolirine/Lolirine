# -*- coding: utf-8 -*-
from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _lolirine_pool_bank(self):
        """Compte bancaire du Pool Store : celui du journal « Ventes Piscines » (LOL),
        sinon le premier compte de la société."""
        self.ensure_one()
        journal = self.env['account.journal'].sudo().search([
            ('code', '=', 'LOL'), ('type', '=', 'sale'), ('company_id', '=', self.id)], limit=1)
        return journal.bank_account_id or self.partner_id.bank_ids[:1]
