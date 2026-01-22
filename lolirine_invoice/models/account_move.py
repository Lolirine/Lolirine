from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging
import base64

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # =============================================
    # CHAMPS ENVOI AUTOMATIQUE
    # =============================================
    
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
    
    # =============================================
    # CHAMPS PEPPOL
    # =============================================
    
    peppol_sent = fields.Boolean(
        string="Envoyé via Peppol",
        default=False,
        help="Indique si la facture a été envoyée via Peppol"
    )
    
    peppol_sent_date = fields.Datetime(
        string="Date envoi Peppol",
        readonly=True,
        help="Date et heure de l'envoi via Peppol"
    )
    
    # =============================================
    # CHAMPS VÉRIFICATION BOX (PRORATA)
    # =============================================
    
    is_prorata_invoice = fields.Boolean(
        string="Facture Prorata",
        default=False,
        help="Indique si cette facture est une facture prorata de résiliation"
    )
    
    box_checked = fields.Boolean(
        string="Box vérifié",
        default=False,
        help="Indique si l'état du box a été vérifié après la résiliation"
    )
    
    box_checked_date = fields.Datetime(
        string="Date vérification box",
        readonly=True,
        help="Date et heure de la vérification du box"
    )
    
    box_checked_by = fields.Many2one(
        'res.users',
        string="Vérifié par",
        readonly=True,
        help="Utilisateur ayant vérifié le box"
    )
    
    # =============================================
    # CHAMPS RETARD ET ECHEANCE
    # =============================================
    
    is_overdue = fields.Boolean(
        string="En retard",
        compute="_compute_overdue_info",
        store=True,
        help="Indique si la facture est en retard de paiement"
    )
    
    days_overdue = fields.Integer(
        string="Jours de retard",
        compute="_compute_overdue_info",
        store=True,
        help="Nombre de jours de retard"
    )
    
    days_until_due = fields.Integer(
        string="Jours avant échéance",
        compute="_compute_overdue_info",
        store=True,
        help="Nombre de jours avant l'échéance"
    )
    
    overdue_level = fields.Selection([
        ('ok', 'OK'),
        ('warning', 'Attention'),
        ('danger', 'En retard'),
        ('critical', 'Critique'),
    ], string="Niveau de retard", compute="_compute_overdue_info", store=True)
    
    # =============================================
    # CHAMPS PENALITES
    # =============================================
    
    penalty_amount = fields.Monetary(
        string="Pénalités de retard",
        compute="_compute_penalty",
        currency_field='currency_id',
        help="Montant des pénalités de retard calculées"
    )
    
    total_with_penalty = fields.Monetary(
        string="Total avec pénalités",
        compute="_compute_penalty",
        currency_field='currency_id',
        help="Montant total incluant les pénalités de retard"
    )
    
    # =============================================
    # CHAMPS RELANCE
    # =============================================
    
    reminder_level = fields.Selection([
        ('0', 'Aucune relance'),
        ('1', '1ère relance'),
        ('2', '2ème relance'),
        ('3', '3ème relance'),
        ('4', 'Mise en demeure'),
    ], string="Niveau de relance", default='0')
    
    last_reminder_date = fields.Date(
        string="Dernière relance",
        help="Date de la dernière relance envoyée"
    )
    
    last_reminder_type = fields.Selection([
        ('email', 'Email'),
        ('letter', 'Courrier'),
        ('phone', 'Téléphone'),
    ], string="Type dernière relance")
    
    next_reminder_date = fields.Date(
        string="Prochaine relance",
        compute="_compute_next_reminder",
        store=True,
        help="Date suggérée pour la prochaine relance"
    )
    
    reminder_count = fields.Integer(
        string="Nombre de relances",
        compute="_compute_reminder_count"
    )
    
    # =============================================
    # CHAMPS TAGS
    # =============================================
    
    invoice_tag_ids = fields.Many2many(
        'lolirine.invoice.tag',
        'account_move_tag_rel',
        'move_id',
        'tag_id',
        string="Tags"
    )
    
    # =============================================
    # CHAMPS NOTES INTERNES
    # =============================================
    
    internal_note = fields.Text(
        string="Note interne",
        help="Note visible uniquement en interne (non imprimée)"
    )
    
    internal_note_important = fields.Boolean(
        string="Note importante",
        default=False,
        help="Marquer cette note comme importante"
    )
    
    # =============================================
    # CHAMPS STATISTIQUES PARTENAIRE
    # =============================================
    
    partner_invoice_count = fields.Integer(
        string="Factures du client",
        compute="_compute_partner_stats"
    )
    
    partner_unpaid_count = fields.Integer(
        string="Impayées du client",
        compute="_compute_partner_stats"
    )

    # =============================================
    # COMPUTE METHODS
    # =============================================

    @api.depends('invoice_date_due', 'state', 'payment_state')
    def _compute_overdue_info(self):
        today = fields.Date.context_today(self)
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund') and move.state == 'posted' and move.payment_state not in ('paid', 'in_payment', 'reversed'):
                if move.invoice_date_due:
                    delta = (today - move.invoice_date_due).days
                    if delta > 0:
                        move.is_overdue = True
                        move.days_overdue = delta
                        move.days_until_due = 0
                        if delta > 60:
                            move.overdue_level = 'critical'
                        elif delta > 30:
                            move.overdue_level = 'danger'
                        elif delta > 14:
                            move.overdue_level = 'warning'
                        else:
                            move.overdue_level = 'warning'
                    else:
                        move.is_overdue = False
                        move.days_overdue = 0
                        move.days_until_due = abs(delta)
                        move.overdue_level = 'ok'
                else:
                    move.is_overdue = False
                    move.days_overdue = 0
                    move.days_until_due = 0
                    move.overdue_level = 'ok'
            else:
                move.is_overdue = False
                move.days_overdue = 0
                move.days_until_due = 0
                move.overdue_level = 'ok'

    def _compute_penalty(self):
        # Taux légal belge (à ajuster selon le taux en vigueur)
        annual_rate = 0.08  # 8% par an
        for move in self:
            if move.is_overdue and move.days_overdue > 0:
                daily_rate = annual_rate / 365
                move.penalty_amount = move.amount_residual * daily_rate * move.days_overdue
                move.total_with_penalty = move.amount_residual + move.penalty_amount
            else:
                move.penalty_amount = 0
                move.total_with_penalty = move.amount_residual

    @api.depends('last_reminder_date', 'reminder_level')
    def _compute_next_reminder(self):
        for move in self:
            if move.last_reminder_date and move.payment_state not in ('paid', 'reversed'):
                # Suggérer une relance 14 jours après la dernière
                move.next_reminder_date = move.last_reminder_date + relativedelta(days=14)
            else:
                move.next_reminder_date = False

    def _compute_reminder_count(self):
        for move in self:
            try:
                move.reminder_count = self.env['lolirine.invoice.reminder'].search_count([('invoice_id', '=', move.id)])
            except Exception:
                move.reminder_count = 0

    def _compute_partner_stats(self):
        for move in self:
            if move.partner_id:
                move.partner_invoice_count = self.search_count([
                    ('partner_id', '=', move.partner_id.id),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('state', '=', 'posted')
                ])
                move.partner_unpaid_count = self.search_count([
                    ('partner_id', '=', move.partner_id.id),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ['not_paid', 'partial'])
                ])
            else:
                move.partner_invoice_count = 0
                move.partner_unpaid_count = 0

    # =============================================
    # ONCHANGE METHODS
    # =============================================

    @api.onchange('partner_id')
    def _onchange_partner_auto_send(self):
        """Hériter les paramètres d'envoi automatique du partenaire"""
        if self.partner_id:
            if hasattr(self.partner_id, 'auto_send_invoice'):
                self.auto_send_invoice = self.partner_id.auto_send_invoice
            if hasattr(self.partner_id, 'auto_send_peppol'):
                self.auto_send_peppol = self.partner_id.auto_send_peppol

    # =============================================
    # ACTION METHODS - VÉRIFICATION BOX
    # =============================================

    def action_check_box(self):
        """Marquer le box comme vérifié"""
        self.ensure_one()
        
        self.write({
            'box_checked': True,
            'box_checked_date': fields.Datetime.now(),
            'box_checked_by': self.env.user.id,
        })
        
        self.message_post(
            body=_("✅ Box vérifié par %s") % self.env.user.name,
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Box vérifié'),
                'message': _("L'état du box a été marqué comme vérifié."),
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }
    
    def action_uncheck_box(self):
        """Annuler la vérification du box"""
        self.ensure_one()
        
        self.write({
            'box_checked': False,
            'box_checked_date': False,
            'box_checked_by': False,
        })
        
        self.message_post(
            body=_("⚠️ Vérification du box annulée par %s") % self.env.user.name,
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Vérification annulée'),
                'message': _('La vérification du box a été annulée.'),
                'type': 'warning',
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }

    # =============================================
    # ACTION METHODS
    # =============================================

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
                            body="📅 Envoi email planifié pour le %s" % send_date,
                            message_type='notification'
                        )
                    else:
                        move._send_invoice_auto()
        
        return res

    def _send_invoice_auto(self):
        """Envoyer la facture automatiquement par email avec le rapport Lolirine attaché"""
        self.ensure_one()
        
        if not self.partner_id.email:
            self.message_post(
                body="⚠️ Envoi automatique impossible : le client n'a pas d'adresse email configurée.",
                message_type='notification'
            )
            return False
        
        try:
            # Récupérer le rapport Lolirine
            lolirine_report = self.env.ref('lolirine_invoice.action_report_invoice_lolirine', raise_if_not_found=False)
            
            if not lolirine_report:
                lolirine_report = self.env.ref('account.account_invoices', raise_if_not_found=False)
            
            # Générer le PDF manuellement
            pdf_content = None
            attachment = None
            
            if lolirine_report:
                pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                    lolirine_report.report_name,
                    [self.id]
                )
                
                if pdf_content:
                    # Créer l'attachement
                    pdf_name = f"Facture_{(self.name or 'Brouillon').replace('/', '_')}.pdf"
                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': pdf_name,
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'account.move',
                        'res_id': self.id,
                        'mimetype': 'application/pdf',
                    })
            
            # Construire le corps de l'email manuellement
            body_html = f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p>Bonjour {self.partner_id.name or ''},</p>
    
    <p>Veuillez trouver en pièce jointe votre facture mensuelle relative à la location de votre box au sein de notre site Lolirine.</p>
    
    <p>Cette facture correspond à la période de location en cours et reprend le détail des prestations facturées, conformément aux conditions prévues dans votre contrat de garde-meubles. Nous vous invitons à en prendre connaissance et à procéder au règlement selon les modalités indiquées sur le document.</p>
    
    <p>Sauf disposition contraire, le paiement est attendu à la date d'échéance mentionnée sur la facture. En cas de retard de paiement, des pénalités pourront être appliquées conformément aux conditions contractuelles.</p>
    
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%; max-width: 400px;">
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Numéro de facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.name or ''}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date de facturation</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_date or ''}</td>
        </tr>
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date d'échéance</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_date_due or ''}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant total</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>{self.amount_total:.2f} EUR</strong></td>
        </tr>
    </table>
    
    <p><strong>Modalités de paiement :</strong></p>
    <ul>
        <li>Communication structurée : {self.payment_reference or self.name or ''}</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
    </ul>
    
    <p>Pour toute question concernant cette facture, votre contrat ou les modalités de paiement, vous pouvez nous contacter à l'adresse suivante : <a href="mailto:gardemeublelolirine@gmail.com">gardemeublelolirine@gmail.com</a> ou par téléphone au 0497/44 41 46 ou 0498/52 11 31.</p>
    
    <p>Nous vous remercions de votre confiance et restons à votre disposition.</p>
    
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
            
            # Créer et envoyer l'email directement
            mail_values = {
                'subject': f"{self.company_id.name or 'Lolirine'} - Facture {self.name or 'Brouillon'}",
                'body_html': body_html,
                'email_from': self.company_id.email or 'gardemeublelolirine@gmail.com',
                'email_to': self.partner_id.email,
                'model': 'account.move',
                'res_id': self.id,
                'auto_delete': False,
            }
            
            if attachment:
                mail_values['attachment_ids'] = [(4, attachment.id)]
            
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
            
            self.write({
                'is_move_sent': True,
                'email_pending': False,
                'email_sent_date': fields.Datetime.now()
            })
            
            self.message_post(
                body="✅ Facture envoyée par email à %s avec PDF Lolirine attaché" % self.partner_id.email,
                message_type='notification'
            )
            return True
            
        except Exception as e:
            _logger.error(f"Erreur envoi email facture {self.name}: {e}")
            self.message_post(
                body="❌ Erreur lors de l'envoi : %s" % str(e),
                message_type='notification'
            )
            return False

    def action_preview_invoice(self):
        """Ouvrir un aperçu PDF de la facture avec le template Lolirine"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        # Forcer l'utilisation du rapport Lolirine
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/lolirine_invoice.report_invoice_lolirine/%s' % self.id,
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
            # Utiliser le rapport Lolirine en HTML
            return {
                'type': 'ir.actions.act_url',
                'url': '/report/html/lolirine_invoice.report_invoice_lolirine/%s' % self.id,
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

    def action_send_invoice_email_now(self):
        """Envoyer la facture par email immédiatement"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit être confirmée avant d'être envoyée."))
        
        result = self._send_invoice_auto()
        
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email envoyé'),
                    'message': _('La facture a été envoyée par email à %s') % self.partner_id.email,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erreur'),
                    'message': _("L'envoi de l'email a échoué. Vérifiez le chatter pour plus de détails."),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    def action_send_peppol(self):
        """Envoyer la facture via Peppol"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit être confirmée avant d'être envoyée."))
        
        if not self.partner_id.peppol_endpoint:
            raise UserError(_("Le client n'a pas d'endpoint Peppol configuré."))
        
        self.write({
            'peppol_sent': True,
            'peppol_sent_date': fields.Datetime.now()
        })
        
        self.message_post(
            body="📤 Facture envoyée via Peppol à %s" % self.partner_id.peppol_endpoint,
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Peppol'),
                'message': _('La facture a été envoyée via Peppol'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_create_reminder(self):
        """Créer une relance pour cette facture"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit être confirmée."))
        
        if self.payment_state == 'paid':
            raise UserError(_("Cette facture est déjà payée."))
        
        current_level = int(self.reminder_level or '0')
        new_level = min(current_level + 1, 4)
        
        self.write({
            'reminder_level': str(new_level),
            'last_reminder_date': fields.Date.context_today(self),
            'last_reminder_type': 'email',
        })
        
        self.message_post(
            body="📧 Relance niveau %s créée" % new_level,
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Relance créée'),
                'message': _('Relance niveau %s créée pour cette facture') % new_level,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_reminders(self):
        """Voir les relances liées à cette facture"""
        self.ensure_one()
        
        return {
            'name': _('Relances'),
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.invoice.reminder',
            'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_view_partner_invoices(self):
        """Voir toutes les factures du partenaire"""
        self.ensure_one()
        
        return {
            'name': _('Factures du client'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted')
            ],
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_move_type': 'out_invoice',
            },
        }

    def action_view_partner_unpaid(self):
        """Voir les factures impayées du partenaire"""
        self.ensure_one()
        
        return {
            'name': _('Factures impayées du client'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ],
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_move_type': 'out_invoice',
            },
        }

    def action_smart_duplicate(self):
        """Dupliquer la facture intelligemment avec mise à jour des dates"""
        self.ensure_one()
        
        new_invoice = self.copy({
            'invoice_date': fields.Date.context_today(self),
            'date': fields.Date.context_today(self),
            'state': 'draft',
            'name': '/',
            'payment_state': 'not_paid',
            'is_move_sent': False,
            'peppol_sent': False,
            'email_pending': False,
            'email_sent_date': False,
            'peppol_sent_date': False,
            'reminder_level': '0',
            'last_reminder_date': False,
            'last_reminder_type': False,
            'is_prorata_invoice': False,
            'box_checked': False,
            'box_checked_date': False,
            'box_checked_by': False,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': new_invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_manual_send_email(self):
        """Bouton pour envoyer manuellement l'email"""
        self.ensure_one()
        return self._send_invoice_auto()

    # =============================================
    # CRON METHODS
    # =============================================

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
