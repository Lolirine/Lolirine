# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    auto_send_invoice_email = fields.Boolean(
        string="Envoi email factures automatique",
        default=False,
        help="Si coché, les factures de ce client seront automatiquement envoyées par email à leur date de facturation."
    )
    
    # Compteur de factures en attente d'envoi
    pending_invoice_count = fields.Integer(
        string="Factures en attente",
        compute='_compute_pending_invoice_count'
    )
    
    def _compute_pending_invoice_count(self):
        for partner in self:
            partner.pending_invoice_count = self.env['account.move'].search_count([
                ('partner_id', '=', partner.id),
                ('email_pending', '=', True),
                ('email_sent', '=', False),
            ])
