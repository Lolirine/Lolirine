# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # =============================================
    # CHAMPS ENVOI EMAIL PLANIFIÉ
    # =============================================
    
    scheduled_email_send = fields.Boolean(
        string="Envoi email planifié",
        default=False,
        copy=False,
        help="Si coché, la facture sera envoyée par email à la date de facturation"
    )
    
    email_send_date = fields.Date(
        string="Date d'envoi email",
        copy=False,
        help="Date à laquelle l'email sera envoyé. Par défaut = date de facturation."
    )
    
    email_pending = fields.Boolean(
        string="En attente d'envoi",
        default=False,
        copy=False,
        help="Indique que la facture est en attente d'envoi automatique"
    )
    
    email_sent = fields.Boolean(
        string="Email envoyé",
        default=False,
        copy=False,
        help="Indique si l'email a été envoyé"
    )
    
    email_sent_date = fields.Datetime(
        string="Date envoi email",
        copy=False,
        readonly=True
    )

    # =============================================
    # OVERRIDE ACTION_POST
    # =============================================
    
    def action_post(self):
        """
        Override pour NE PAS envoyer immédiatement.
        Marque la facture comme "en attente d'envoi" si l'option est activée.
        L'envoi réel se fait via le cron à la date de facturation.
        """
        res = super().action_post()
        
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                # Hériter du paramètre client si pas déjà défini
                if not move.scheduled_email_send and move.partner_id.auto_send_invoice_email:
                    move.scheduled_email_send = True
                
                # Si envoi planifié activé, marquer comme en attente
                if move.scheduled_email_send:
                    # Définir la date d'envoi = date de facturation si pas définie
                    if not move.email_send_date:
                        move.email_send_date = move.invoice_date or fields.Date.today()
                    
                    move.email_pending = True
                    
                    move.message_post(
                        body=_("📧 Envoi email planifié pour le %s") % move.email_send_date,
                        message_type='notification'
                    )
                    
                    _logger.info(f"Facture {move.name} : envoi email planifié pour {move.email_send_date}")
        
        return res

    # =============================================
    # MÉTHODE ENVOI EMAIL
    # =============================================
    
    def _send_invoice_email(self):
        """Envoyer la facture par email"""
        self.ensure_one()
        
        if not self.partner_id.email:
            self.message_post(
                body=_("❌ Envoi impossible : le client n'a pas d'adresse email."),
                message_type='notification'
            )
            _logger.warning(f"Facture {self.name} : pas d'email pour {self.partner_id.name}")
            return False
        
        # Chercher le template Lolirine
        template = self.env.ref(
            'lolirine_email_templates.email_template_facture_mensuelle',
            raise_if_not_found=False
        )
        
        # Fallback sur le template standard Odoo
        if not template:
            template = self.env.ref(
                'account.email_template_edi_invoice',
                raise_if_not_found=False
            )
        
        if not template:
            self.message_post(
                body=_("❌ Aucun template email trouvé."),
                message_type='notification'
            )
            return False
        
        try:
            template.send_mail(self.id, force_send=True)
            
            self.write({
                'email_sent': True,
                'email_sent_date': fields.Datetime.now(),
                'email_pending': False,
                'is_move_sent': True,
            })
            
            self.message_post(
                body=_("✅ Facture envoyée par email à %s") % self.partner_id.email,
                message_type='notification'
            )
            
            _logger.info(f"Facture {self.name} envoyée par email à {self.partner_id.email}")
            return True
            
        except Exception as e:
            self.message_post(
                body=_("❌ Erreur lors de l'envoi : %s") % str(e),
                message_type='notification'
            )
            _logger.error(f"Erreur envoi facture {self.name} : {e}")
            return False

    # =============================================
    # ENVOI MANUEL
    # =============================================
    
    def action_send_invoice_email_now(self):
        """Bouton pour envoyer l'email immédiatement"""
        self.ensure_one()
        result = self._send_invoice_email()
        
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Email envoyé"),
                    'message': _("La facture a été envoyée à %s") % self.partner_id.email,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Erreur"),
                    'message': _("L'envoi a échoué. Vérifiez le chatter pour plus de détails."),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    # =============================================
    # CRON - ENVOI AUTOMATIQUE PLANIFIÉ
    # =============================================
    
    @api.model
    def _cron_send_scheduled_invoices(self):
        """
        Cron exécuté quotidiennement.
        Envoie les factures dont la date d'envoi est atteinte.
        """
        _logger.info("=== CRON: Début envoi factures planifiées ===")
        
        today = fields.Date.today()
        
        # Chercher les factures à envoyer
        invoices_to_send = self.search([
            ('email_pending', '=', True),
            ('email_sent', '=', False),
            ('email_send_date', '<=', today),
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
        ])
        
        _logger.info(f"Factures à envoyer aujourd'hui : {len(invoices_to_send)}")
        
        sent_count = 0
        error_count = 0
        
        for invoice in invoices_to_send:
            try:
                if invoice._send_invoice_email():
                    sent_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                _logger.error(f"Erreur cron pour {invoice.name} : {e}")
        
        _logger.info(f"=== CRON terminé: {sent_count} envoyées, {error_count} erreurs ===")
        
        return True
