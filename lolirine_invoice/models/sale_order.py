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
    # EMAIL DE BIENVENUE
    # =============================================
    
    def _send_welcome_email(self):
        """Envoyer l'email de bienvenue automatiquement après confirmation de l'abonnement"""
        self.ensure_one()
        
        if not self.partner_id.email:
            self.message_post(
                body=_("⚠️ Envoi email de bienvenue impossible : le client n'a pas d'adresse email."),
                message_type='notification'
            )
            return False
        
        try:
            # Récupérer les infos du box
            box_name = self.order_line[0].product_id.name if self.order_line else "votre box"
            start_date = self.start_date.strftime('%d/%m/%Y') if self.start_date else 'À définir'
            portal_url = self.get_portal_url()
            
            # Construire le corps de l'email
            body_html = f"""
<div style="font-family: Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.6;">
    <p>Bonjour {self.partner_id.name or ''},</p>
    
    <p>Toute l'équipe vous souhaite la bienvenue et vous remercie de votre confiance !</p>
    
    <p>Nous avons le plaisir de confirmer l'activation de votre contrat pour le box de stockage 
    <strong>{box_name}</strong>.</p>
    
    <p>Voici un résumé des informations utiles :</p>
    <ul>
        <li><strong>Date de début :</strong> {start_date}</li>
        <li><strong>Votre site de stockage :</strong> Rue Drève Boninas 2, 5021 Boninne</li>
        <li><strong>Horaires d'accès :</strong> 24H/24 et 7J/7</li>
    </ul>
    
    <p>Votre première facture sera générée prochainement. Vous pouvez à tout moment consulter vos documents, gérer votre abonnement et mettre à jour vos informations depuis votre portail client personnel.</p>
    
    <p>Votre Code d'accès vous sera fourni sur place, lors de la signature de votre contrat. Vous pouvez prendre contact avec nos services soit en ligne soit par téléphone pour convenir d'un rendez-vous.</p>
    
    <p style="margin: 20px 0;">
        <a href="{portal_url}" style="background-color: #875a7b; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
            Accéder à mon portail client
        </a>
    </p>
    
    <p>N'hésitez pas à nous contacter si vous avez la moindre question.</p>
    
    <p>Cordialement,</p>
    
    <div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #dee2e6;">
        <p style="margin: 0;">
            <strong style="color: #495057;">Lolirine Garde-Meubles</strong><br/>
            <span style="color: #6c757d;">Feron Rodney</span><br/>
            <span style="color: #6c757d;">Tél. : 0497/44 41 46 - 0498/52 11 31</span><br/>
            <span style="color: #6c757d;">Email : <a href="mailto:gardemeublelolirine@gmail.com" style="color: #007bff;">gardemeublelolirine@gmail.com</a></span>
        </p>
    </div>
</div>
"""
            
            # Créer et envoyer l'email
            mail_values = {
                'subject': f"Bienvenue ! Votre accès au box {box_name}",
                'body_html': body_html,
                'email_from': self.company_id.email_formatted or self.env.company.email_formatted or 'notifications@lolirine-lolirine.odoo.com',
                'email_to': self.partner_id.email,
                'model': 'sale.order',
                'res_id': self.id,
                'auto_delete': False,
            }
            
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            
            self.message_post(
                body=_("✅ Email de bienvenue envoyé à %s") % self.partner_id.email,
                message_type='notification'
            )
            
            _logger.info(f"Email de bienvenue envoyé pour {self.name} à {self.partner_id.email}")
            return True
            
        except Exception as e:
            _logger.error(f"Erreur envoi email bienvenue {self.name}: {e}")
            self.message_post(
                body=_("❌ Erreur lors de l'envoi de l'email de bienvenue : %s") % str(e),
                message_type='notification'
            )
            return False
    
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
