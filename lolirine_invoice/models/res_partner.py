# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # =============================================
    # CHAMPS ENVOI AUTOMATIQUE
    # =============================================
    
    auto_send_invoice = fields.Boolean(
        string="Envoi auto factures email",
        default=False,
        help="Si coché, les factures de ce client seront envoyées automatiquement par email à leur date de facturation"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi auto factures Peppol",
        default=False,
        help="Si coché, les factures de ce client seront envoyées automatiquement via Peppol après confirmation"
    )

    # =============================================
    # CHAMPS PEPPOL
    # =============================================
    
    peppol_eas = fields.Selection(
        selection=[
            ('0208', '0208 - BE:EN (Belgique)'),
            ('0009', '0009 - FR:SIRET (France)'),
            ('0088', '0088 - EAN (International)'),
            ('0190', '0190 - NL:KVK (Pays-Bas)'),
            ('0106', '0106 - DE:LID (Allemagne)'),
        ],
        string="EAS (Schéma)",
        help="Electronic Address Scheme - Type d'identifiant Peppol"
    )
    
    peppol_endpoint = fields.Char(
        string="Endpoint Peppol",
        help="Identifiant Peppol du destinataire (ex: numéro d'entreprise belge sans espaces)"
    )

    # =============================================
    # CHAMPS STATISTIQUES IMPAYÉS
    # =============================================
    
    invoice_overdue_count = fields.Integer(
        string="Factures en retard",
        compute='_compute_invoice_overdue_stats'
    )
    
    invoice_overdue_amount = fields.Monetary(
        string="Montant impayé en retard",
        compute='_compute_invoice_overdue_stats'
    )

    def _compute_invoice_overdue_stats(self):
        for partner in self:
            overdue_invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'not in', ['paid', 'reversed']),
                ('is_overdue', '=', True),
            ])
            partner.invoice_overdue_count = len(overdue_invoices)
            partner.invoice_overdue_amount = sum(overdue_invoices.mapped('amount_residual'))
