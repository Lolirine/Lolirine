# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    """
    Extension des abonnements (sale.order avec is_subscription=True)
    pour ajouter l'option d'envoi email automatique.
    """
    _inherit = 'sale.order'

    auto_send_invoice_email = fields.Boolean(
        string="Envoi email factures automatique",
        default=False,
        help="Si coché, les factures générées par cet abonnement seront automatiquement envoyées par email à leur date de facturation."
    )
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Override pour hériter de l'option d'envoi email
        vers les factures créées.
        """
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        
        for move in moves:
            # Hériter de l'option de l'abonnement
            subscription = self.filtered(lambda s: s.partner_id == move.partner_id)
            if subscription and subscription[0].auto_send_invoice_email:
                move.write({
                    'scheduled_email_send': True,
                    'email_pending': True,
                    'email_send_date': move.invoice_date or fields.Date.today(),
                })
            # Ou hériter du client
            elif move.partner_id.auto_send_invoice_email:
                move.write({
                    'scheduled_email_send': True,
                    'email_pending': True,
                    'email_send_date': move.invoice_date or fields.Date.today(),
                })
        
        return moves
