from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    auto_send_invoice = fields.Boolean(
        string="Envoi auto factures email",
        default=False,
        help="Si coche, les factures generees par cet abonnement seront envoyees automatiquement par email"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi auto Peppol",
        default=False,
        help="Si active, les factures generees seront envoyees automatiquement via Peppol"
    )
    
    @api.onchange('partner_id')
    def _onchange_partner_auto_send(self):
        if self.partner_id:
            if hasattr(self.partner_id, 'auto_send_invoice'):
                self.auto_send_invoice = self.partner_id.auto_send_invoice
            if hasattr(self.partner_id, 'auto_send_peppol'):
                self.auto_send_peppol = self.partner_id.auto_send_peppol
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        
        for move in moves:
            auto_email = self.auto_send_invoice or move.partner_id.auto_send_invoice
            auto_peppol = self.auto_send_peppol or move.partner_id.auto_send_peppol
            
            if auto_email or auto_peppol:
                move.write({
                    'auto_send_invoice': auto_email,
                    'auto_send_peppol': auto_peppol,
                })
        
        return moves
