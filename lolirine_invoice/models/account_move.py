from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    auto_send_invoice = fields.Boolean(
        string="📧 Envoi Email automatique",
        default=False,
        help="Si activé, la facture sera envoyée automatiquement par email après confirmation"
    )
    
    auto_send_peppol = fields.Boolean(
        string="🔄 Envoi Peppol automatique",
        default=False,
        help="Si activé, la facture sera envoyée automatiquement via Peppol après confirmation"
    )
    
    email_scheduled_date = fields.Date(
        string="Date d'envoi email",
        help="Date à laquelle l'email sera envoyé. Si vide, utilise la date de facturation."
    )
    
    email_pending = fields.Boolean(
        string="⏳ Email en attente",
        default=False,
        help="Indique que l'email est en attente d'envoi"
    )
    
    email_sent_date = fields.Datetime(
        string="📧 Date envoi email",
        readonly=True,
        help="Date et heure de l'envoi effectif de l'email"
    )
    
    is_overdue = fields.Boolean(
        string="En retard",
        compute="_compute_is_overdue",
        store=True,
        help="Indique si la facture est en retard de paiement"
    )
    
    days_overdue = fields.Integer(
        string="Jours de retard",
        compute="_compute_is_overdue",
        store=True,
        help="Nombre de jours de retard"
    )

    @api.depends('invoice_date_due', 'state', 'payment_state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund') and move.state == 'posted' and move.payment_state not in ('paid', 'in_payment', 'reversed'):
                if move.invoice_date_due and move.invoice_date_due < today:
                    move.is_overdue = True
                    move.days_overdue = (today - move.invoice_date_due).days
                else:
                    move.is_overdue = False
                    move.days_overdue = 0
            else:
                move.is_overdue = False
                move.days_overdue = 0

    @api.onchange('partner_id')
    def _onchange_partner_auto_send(self):
        """Hériter les paramètres d'envoi automatique du partenaire"""
        if self.partner_id:
            if hasattr(self.partner_id, 'auto_send_invoice'):
                self.auto_send_invoice = self.partner_id.auto_send_invoice
            if hasattr(self.partner_id, 'auto_send_peppol'):
                self.auto_send_peppol = self.partner_id.auto_send_peppol

    def action_post(self):
        """Override pour gérer l'envoi automatique après confirmation"""
        res = super().action_post()
        
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                send_date = move.email_scheduled_date or move.invoice_date
                today = fields.Date.context_today(self)
                
                if move.auto_send_invoice:
                    if send_date and send_date > today:
                        move.email_pending = True
                        move.message_post(
                            body=_("📅 Envoi email planifié pour le %s") % send_date,
                            message_type='notification'
                        )
                    else:
                        move._send_invoice_auto()
        
        return res

    def _send_invoice_auto(self):
        """Envoyer la facture automatiquement par email"""
        self.ensure_one()
        
        if not self.partner_id.email:
            self.message_post(
                body=_("⚠️ Envoi automatique impossible : le client n'a pas d'adresse email configurée."),
                message_type='notification'
            )
            return False
        
        template = None
        template_refs = [
            'account.email_template_edi_invoice',
            'sale.email_template_edi_invoice',
        ]
        
        for ref in template_refs:
            template = self.env.ref(ref, raise_if_not_found=False)
            if template:
                _logger.info(f"Template trouvé: {ref}")
                break
        
        if not template:
            template = self.env['mail.template'].search([
                ('model_id.model', '=', 'account.move'),
                ('name', 'ilike', 'facture')
            ], limit=1)
        
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                self.write({
                    'is_move_sent': True,
                    'email_pending': False,
                    'email_sent_date': fields.Datetime.now()
                })
                self.message_post(
                    body=_("✅ Facture envoyée automatiquement par email à %s") % self.partner_id.email,
                    message_type='notification'
                )
                return True
            except Exception as e:
                _logger.error(f"Erreur envoi email facture {self.name}: {e}")
                self.message_post(
                    body=_("❌ Erreur lors de l'envoi automatique : %s") % str(e),
                    message_type='notification'
                )
                return False
        else:
            self.message_post(
                body=_("⚠️ Aucun template d'email trouvé pour l'envoi automatique."),
                message_type='notification'
            )
            return False

    def action_preview_invoice(self):
        """Ouvrir un aperçu PDF de la facture"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/account.report_invoice/%s' % self.id,
            'target': 'new',
        }

    def action_preview_invoice_html(self):
        """Ouvrir un aperçu HTML de la facture dans le portail"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        if self.state == 'posted':
            return {
                'type': 'ir.actions.act_url',
                'url': '/my/invoices/%s' % self.id,
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': '/report/html/account.report_invoice/%s' % self.id,
                'target': 'new',
            }

    def action_confirm_and_send(self):
        """Confirmer la facture et ouvrir le wizard d'envoi"""
        self.ensure_one()
        
        if self.state == 'draft':
            self.action_post()
        
        return self.action_open_send_wizard()

    def action_open_send_wizard(self):
        """Ouvrir le wizard d'envoi de facture"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit être confirmée avant d'être envoyée."))
        
        return {
            'name': _('Envoyer la facture'),
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.invoice.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_email': self.partner_id.email,
            },
        }

    def action_send_invoice_email(self):
        """Envoyer la facture par email avec le composer standard"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit être confirmée avant d'être envoyée."))
        
        template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        
        if not template:
            template = self.env.ref('lolirine_invoice.email_template_invoice_lolirine', raise_if_not_found=False)
        
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=False)
        
        ctx = {
            'default_model': 'account.move',
            'default_res_ids': self.ids,
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'mark_invoice_as_sent': True,
            'force_email': True,
        }
        
        return {
            'name': _('Envoyer la facture par email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_manual_send_email(self):
        """Bouton pour envoyer manuellement l'email"""
        self.ensure_one()
        return self._send_invoice_auto()

    @api.model
    def _cron_send_pending_emails(self):
        """Cron pour envoyer les factures en attente"""
        today = fields.Date.context_today(self)
        
        pending_invoices = self.search([
            ('email_pending', '=', True),
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            '|',
            ('email_scheduled_date', '<=', today),
            '&',
            ('email_scheduled_date', '=', False),
            ('invoice_date', '<=', today)
        ])
        
        _logger.info(f"Cron envoi emails: {len(pending_invoices)} factures à traiter")
        
        for invoice in pending_invoices:
            try:
                invoice._send_invoice_auto()
            except Exception as e:
                _logger.error(f"Erreur cron envoi facture {invoice.name}: {e}")
        
        return True
