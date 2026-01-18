# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # =============================================
    # CHAMPS ENVOI AUTOMATIQUE SUR ABONNEMENT
    # =============================================
    
    auto_send_invoice = fields.Boolean(
        string="Envoi auto factures email",
        default=False,
        help="Si coché, les factures générées par cet abonnement seront envoyées automatiquement par email"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi auto factures Peppol",
        default=False,
        help="Si coché, les factures générées par cet abonnement seront envoyées automatiquement via Peppol"
    )

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Override pour propager les options d'envoi auto vers la facture"""
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        
        for move in moves:
            # Priorité : abonnement > client
            auto_email = self.auto_send_invoice or move.partner_id.auto_send_invoice
            auto_peppol = self.auto_send_peppol or move.partner_id.auto_send_peppol
            
            if auto_email or auto_peppol:
                move.write({
                    'auto_send_invoice': auto_email,
                    'auto_send_peppol': auto_peppol,
                })
        
        return moves
