# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # =============================================
    # CHAMPS ENVOI AUTOMATIQUE
    # =============================================
    
    auto_send_invoice = fields.Boolean(
        string="Envoi Email automatique",
        default=False,
        help="Si coché, la facture sera envoyée automatiquement par email à la date de facturation"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi Peppol automatique",
        default=False,
        help="Si coché, la facture sera envoyée automatiquement via Peppol après confirmation"
    )
    
    peppol_sent = fields.Boolean(
        string="Envoyée via Peppol",
        default=False,
        copy=False,
    )
    
    peppol_sent_date = fields.Datetime(
        string="Date envoi Peppol",
        copy=False
    )

    # =============================================
    # CHAMPS ENVOI DIFFÉRÉ
    # =============================================
    
    email_scheduled_date = fields.Date(
        string="Date d'envoi email prévue",
        copy=False,
        help="Date à laquelle l'email sera envoyé automatiquement. Par défaut = date de facturation."
    )
    
    email_pending = fields.Boolean(
        string="Email en attente",
        default=False,
        copy=False,
        help="Facture en attente d'envoi automatique (le cron l'enverra à la date prévue)"
    )
    
    email_sent_date = fields.Datetime(
        string="Date envoi email",
        copy=False,
        readonly=True
    )

    # =============================================
    # CHAMPS TAGS ET NOTES
    # =============================================
    
    invoice_tag_ids = fields.Many2many(
        'lolirine.invoice.tag',
        string="Tags",
        help="Tags pour catégoriser les factures"
    )
    
    internal_note = fields.Text(
        string="Note interne",
        help="Note visible uniquement en interne"
    )
    
    internal_note_important = fields.Boolean(
        string="Note importante",
        default=False
    )

    # =============================================
    # CHAMPS RELANCES
    # =============================================
    
    reminder_ids = fields.One2many(
        'lolirine.invoice.reminder',
        'invoice_id',
        string="Relances"
    )
    
    reminder_count = fields.Integer(
        string="Nombre de relances",
        compute='_compute_reminder_count'
    )
    
    last_reminder_date = fields.Date(
        string="Dernière relance",
        compute='_compute_reminder_info',
        store=True
    )
    
    last_reminder_type = fields.Selection(
        selection=[
            ('email', 'Email'),
            ('sms', 'SMS'),
            ('phone', 'Téléphone'),
            ('mail', 'Courrier'),
        ],
        string="Type dernière relance",
        compute='_compute_reminder_info',
        store=True
    )
    
    next_reminder_date = fields.Date(
        string="Prochaine relance",
        compute='_compute_next_reminder'
    )

    # =============================================
    # CHAMPS RETARD ET PÉNALITÉS
    # =============================================
    
    days_until_due = fields.Integer(
        string="Jours avant échéance",
        compute='_compute_overdue_info'
    )
    
    days_overdue = fields.Integer(
        string="Jours de retard",
        compute='_compute_overdue_info'
    )
    
    is_overdue = fields.Boolean(
        string="En retard",
        compute='_compute_overdue_info',
        store=True
    )
    
    overdue_level = fields.Selection(
        selection=[
            ('ok', 'OK'),
            ('warning', 'Attention'),
            ('danger', 'Urgent'),
            ('critical', 'Critique'),
        ],
        string="Niveau de retard",
        compute='_compute_overdue_info'
    )
    
    penalty_rate = fields.Float(
        string="Taux de pénalité (%)",
        default=10.0
    )
    
    penalty_amount = fields.Monetary(
        string="Montant pénalités",
        compute='_compute_penalty'
    )
    
    total_with_penalty = fields.Monetary(
        string="Total avec pénalités",
        compute='_compute_penalty'
    )

    # =============================================
    # CHAMPS STATISTIQUES CLIENT
    # =============================================
    
    partner_invoice_count = fields.Integer(
        string="Factures du client",
        compute='_compute_partner_stats'
    )
    
    partner_unpaid_count = fields.Integer(
        string="Impayées du client",
        compute='_compute_partner_stats'
    )

    # =============================================
    # OVERRIDE ACTION_POST - ENVOI DIFFÉRÉ
    # =============================================
    
    def action_post(self):
        """
        Override pour gérer l'envoi différé.
        Si auto_send_invoice est coché :
        - Si date_facturation <= aujourd'hui → Envoyer immédiatement
        - Si date_facturation > aujourd'hui → Marquer en attente pour le cron
        """
        res = super().action_post()
        
        today = fields.Date.today()
        
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                
                # === ENVOI PEPPOL (toujours immédiat si activé) ===
                if move.auto_send_peppol:
                    move._send_invoice_peppol_auto()
                
                # === ENVOI EMAIL (différé selon date de facturation) ===
                if move.auto_send_invoice:
                    invoice_date = move.invoice_date or today
                    
                    if invoice_date <= today:
                        # Date passée ou aujourd'hui → Envoyer immédiatement
                        move._send_invoice_email()
                    else:
                        # Date future → Planifier l'envoi pour le cron
                        move.write({
                            'email_pending': True,
                            'email_scheduled_date': invoice_date,
                        })
                        move.message_post(
                            body=_("📧 Envoi email planifié pour le %s") % invoice_date,
                            message_type='notification'
                        )
                        _logger.info(f"Facture {move.name} : envoi email planifié pour {invoice_date}")
        
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
        
        # Chercher le template (ordre de priorité)
        template = None
        template_refs = [
            'lolirine_email_templates.email_template_facture_mensuelle',
            'lolirine_invoice.email_template_invoice',
            'account.email_template_edi_invoice',
        ]
        
        for ref in template_refs:
            template = self.env.ref(ref, raise_if_not_found=False)
            if template:
                break
        
        if not template:
            self.message_post(
                body=_("❌ Aucun template email trouvé."),
                message_type='notification'
            )
            return False
        
        try:
            template.send_mail(self.id, force_send=True)
            
            self.write({
                'is_move_sent': True,
                'email_sent_date': fields.Datetime.now(),
                'email_pending': False,
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

    def _send_invoice_peppol_auto(self):
        """Envoyer la facture automatiquement via Peppol"""
        self.ensure_one()
        
        if not self.partner_id.peppol_endpoint:
            self.message_post(
                body=_("❌ Envoi Peppol impossible : endpoint non configuré pour ce client."),
                message_type='notification'
            )
            return False
        
        self.write({
            'peppol_sent': True,
            'peppol_sent_date': fields.Datetime.now(),
        })
        
        self.message_post(
            body=_("✅ Facture envoyée via Peppol"),
            message_type='notification'
        )
        
        return True

    # =============================================
    # CRON - ENVOI AUTOMATIQUE PLANIFIÉ
    # =============================================
    
    @api.model
    def _cron_send_scheduled_invoices(self):
        """
        Cron exécuté quotidiennement (7h00).
        Envoie les factures dont la date d'envoi est atteinte.
        """
        _logger.info("=== CRON: Début envoi factures planifiées ===")
        
        today = fields.Date.today()
        
        invoices_to_send = self.search([
            ('email_pending', '=', True),
            ('email_scheduled_date', '<=', today),
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

    # =============================================
    # BOUTON ENVOI MANUEL
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
                    'message': _("L'envoi a échoué. Vérifiez le chatter."),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    # =============================================
    # COMPUTE METHODS
    # =============================================
    
    def _compute_reminder_count(self):
        for move in self:
            move.reminder_count = len(move.reminder_ids)
    
    @api.depends('reminder_ids', 'reminder_ids.date', 'reminder_ids.reminder_type')
    def _compute_reminder_info(self):
        for move in self:
            if move.reminder_ids:
                last = move.reminder_ids.sorted('date', reverse=True)[0]
                move.last_reminder_date = last.date
                move.last_reminder_type = last.reminder_type
            else:
                move.last_reminder_date = False
                move.last_reminder_type = False
    
    def _compute_next_reminder(self):
        for move in self:
            if move.payment_state == 'paid' or move.state != 'posted':
                move.next_reminder_date = False
            elif move.last_reminder_date:
                move.next_reminder_date = move.last_reminder_date + timedelta(days=7)
            elif move.invoice_date_due:
                move.next_reminder_date = move.invoice_date_due + timedelta(days=3)
            else:
                move.next_reminder_date = False
    
    @api.depends('invoice_date_due', 'payment_state', 'state')
    def _compute_overdue_info(self):
        today = fields.Date.today()
        for move in self:
            if move.invoice_date_due and move.state == 'posted' and move.payment_state not in ('paid', 'reversed'):
                delta = (move.invoice_date_due - today).days
                move.days_until_due = max(delta, 0)
                move.days_overdue = max(-delta, 0)
                move.is_overdue = delta < 0
                
                if delta >= 0:
                    move.overdue_level = 'ok'
                elif delta >= -7:
                    move.overdue_level = 'warning'
                elif delta >= -30:
                    move.overdue_level = 'danger'
                else:
                    move.overdue_level = 'critical'
            else:
                move.days_until_due = 0
                move.days_overdue = 0
                move.is_overdue = False
                move.overdue_level = 'ok'
    
    def _compute_penalty(self):
        for move in self:
            if move.is_overdue and move.amount_residual > 0:
                move.penalty_amount = move.amount_residual * (move.penalty_rate / 100)
                move.total_with_penalty = move.amount_residual + move.penalty_amount
            else:
                move.penalty_amount = 0
                move.total_with_penalty = move.amount_residual
    
    def _compute_partner_stats(self):
        for move in self:
            if move.partner_id:
                invoices = self.search([
                    ('partner_id', '=', move.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                ])
                move.partner_invoice_count = len(invoices)
                move.partner_unpaid_count = len(invoices.filtered(lambda i: i.payment_state not in ('paid', 'reversed')))
            else:
                move.partner_invoice_count = 0
                move.partner_unpaid_count = 0

    # =============================================
    # ACTIONS EXISTANTES
    # =============================================

    def action_preview_invoice(self):
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/account.report_invoice/%s' % self.id,
            'target': 'new',
        }

    def action_preview_invoice_html(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_portal_url(),
            'target': 'new',
        }

    def action_confirm_and_send(self):
        self.ensure_one()
        if self.state == 'draft':
            self.action_post()
        return self.action_open_send_wizard()

    def action_open_send_wizard(self):
        self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Envoyer la facture'),
            'res_model': 'account.move.send',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'default_mail_template_id': template.id if template else False,
            },
        }

    def action_send_peppol(self):
        self.ensure_one()
        return self._send_invoice_peppol_auto()

    def action_create_reminder(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle relance'),
            'res_model': 'lolirine.invoice.reminder',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_view_reminders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Relances'),
            'res_model': 'lolirine.invoice.reminder',
            'view_mode': 'tree,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {'default_invoice_id': self.id},
        }

    def action_view_partner_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factures de %s') % self.partner_id.name,
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('move_type', '=', 'out_invoice'),
            ],
        }

    def action_view_partner_unpaid(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Impayées de %s') % self.partner_id.name,
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'not in', ['paid', 'reversed']),
            ],
        }

    def action_smart_duplicate(self):
        self.ensure_one()
        new_invoice = self.copy({
            'invoice_date': fields.Date.today(),
            'date': fields.Date.today(),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle facture'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': new_invoice.id,
        }
