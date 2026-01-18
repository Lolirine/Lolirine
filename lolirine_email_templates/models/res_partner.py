# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    auto_send_invoice_email = fields.Boolean(
        string="Envoi email factures automatique",
        default=False,
        help="Si coché, les factures de ce client seront automatiquement envoyées par email à leur date de facturation."
    )
