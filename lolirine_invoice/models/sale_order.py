# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date
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
    
    # =============================================
    # RÉSILIATION AVEC PRORATA
    # =============================================
    
    def action_terminate_with_prorata(self):
        """
        Résilier l'abonnement avec facturation prorata + clôture automatique.
        Calcule les jours utilisés et génère une facture finale.
        """
        self.ensure_one()
        
        if not self.is_subscription:
            raise UserError(_("Cette action est uniquement disponible pour les abonnements."))
        
        if self.subscription_state != '3_progress':
            raise UserError(_("L'abonnement doit être en cours pour être résilié."))
        
        if not self.end_date:
            raise UserError(_("Veuillez d'abord définir une date de fin (end_date) pour l'abonnement."))
        
        # Date de début de la période = dernière facture ou start_date
        last_invoice_date = self.last_invoice_date or self.start_date
        end_date = self.end_date
        
        if end_date <= last_invoice_date:
            raise UserError(_("La date de fin doit être postérieure à la dernière date de facturation (%s).") % last_invoice_date)
        
        days_used = (end_date - last_invoice_date).days
        days_in_month = 30  # Base 30 jours
        
        # Créer les lignes de facture prorata
        invoice_lines = []
        for line in self.order_line:
            if line.product_uom_qty <= 0:
                continue
                
            # Calculer le montant prorata
            monthly_price = line.price_unit
            prorata_price = round((days_used / days_in_month) * monthly_price, 2)
            
            invoice_lines.append((0, 0, {
                'name': f"{line.name}\nProrata du {last_invoice_date} au {end_date} ({days_used} jours)",
                'product_id': line.product_id.id,
                'quantity': line.product_uom_qty,
                'price_unit': prorata_price,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
            }))
        
        if not invoice_lines:
            raise UserError(_("Aucune ligne à facturer."))
        
        # Créer la facture prorata
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': date.today(),
            'invoice_origin': self.name,
            'narration': f"Facture de résiliation - Prorata {days_used} jours",
            'invoice_line_ids': invoice_lines,
            'is_prorata_invoice': True,  # Marquer comme facture prorata
        }
        
        invoice = self.env['account.move'].sudo().create(invoice_vals)
        
        # Clôturer l'abonnement
        close_reason = self.env['sale.order.close.reason'].search([('name', 'ilike', 'Fin du contrat')], limit=1)
        self.set_close(close_reason_id=close_reason.id if close_reason else None)
        
        # Poster un message
        self.message_post(
            body=_("📄 Facture prorata de résiliation créée: %s (%.2f€ TTC pour %d jours) - Abonnement clôturé") % (
                invoice.name or 'Brouillon',
                invoice.amount_total,
                days_used
            ),
            message_type='notification'
        )
        
        _logger.info(f"Facture prorata créée pour {self.name}: {invoice.amount_total}€ TTC ({days_used} jours) - Abonnement clôturé")
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture Prorata'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_terminate_and_close(self):
        """
        Clôturer l'abonnement SANS facture prorata.
        Utilisé quand le client a déjà payé le mois complet ou qu'on ne facture pas le prorata.
        """
        self.ensure_one()
        
        if not self.is_subscription:
            raise UserError(_("Cette action est uniquement disponible pour les abonnements."))
        
        if self.subscription_state != '3_progress':
            raise UserError(_("L'abonnement doit être en cours pour être résilié."))
        
        # Clôturer l'abonnement
        close_reason = self.env['sale.order.close.reason'].search([('name', 'ilike', 'Fin du contrat')], limit=1)
        self.set_close(close_reason_id=close_reason.id if close_reason else None)
        
        self.message_post(
            body=_("🔒 Abonnement clôturé sans facture prorata."),
            message_type='notification'
        )
        
        _logger.info(f"Abonnement {self.name} clôturé sans prorata")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Abonnement clôturé'),
                'message': _("L'abonnement %s a été clôturé.") % self.name,
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }
