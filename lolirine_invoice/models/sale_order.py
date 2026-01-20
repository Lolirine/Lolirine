# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


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

    # =============================================
    # PATCH: Correction bug Odoo Enterprise set_close()
    # =============================================
    
    def set_close(self, close_reason_id=None, renew=False, **kwargs):
        """
        PATCH CRITIQUE: Corrige le bug Odoo Enterprise où set_close() a des 
        signatures incompatibles entre les modules:
        - sale_subscription: set_close(self) - 1 argument
        - project_sale_subscription: appelle super().set_close(close_reason_id, renew) - 3 arguments
        - sale_subscription_partnership: passe *args, **kwargs
        
        Résultat: TypeError: takes 1 positional argument but 3 were given
        
        SOLUTION: Cette méthode n'appelle PAS super() pour éviter la chaîne 
        d'héritage bugguée. Elle implémente directement la logique de fermeture.
        """
        for subscription in self:
            # Ne traiter que les abonnements (pas les commandes normales)
            if hasattr(subscription, 'is_subscription') and not subscription.is_subscription:
                continue
            
            # Préparer les valeurs de mise à jour
            vals = {
                'subscription_state': '6_churn',  # État "Churned" / Résilié
            }
            
            # Ajouter la raison de clôture si fournie
            if close_reason_id:
                vals['close_reason_id'] = close_reason_id
            
            # Mettre à jour l'abonnement
            subscription.write(vals)
            
            # Poster un message dans le chatter
            msg = _("Abonnement clôturé.")
            if close_reason_id:
                try:
                    reason = self.env['sale.order.close.reason'].browse(close_reason_id)
                    if reason.exists():
                        msg = _("Abonnement clôturé. Raison: %s") % reason.name
                except Exception:
                    pass
            
            subscription.message_post(
                body=msg,
                message_type='notification'
            )
            
            _logger.info(f"Abonnement {subscription.name} clôturé via patch set_close()")
        
        return True
