# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)

GARDE_MEUBLE_JOURNAL_ID = 9


class AccountMove(models.Model):
    _inherit = "account.move"

    # ==================== CHAMPS EXISTANTS ====================
    
    auto_send_invoice = fields.Boolean(
        string="Envoi automatique",
        default=False,
        help="Si active, la facture sera envoyee automatiquement par email apres confirmation"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi automatique Peppol",
        default=False,
        help="Si active, la facture sera envoyee automatiquement via Peppol apres confirmation"
    )
    
    peppol_sent = fields.Boolean(
        string="Envoyee via Peppol",
        default=False,
        copy=False,
        help="Indique si la facture a ete envoyee via Peppol"
    )
    
    peppol_sent_date = fields.Datetime(
        string="Date envoi Peppol",
        copy=False
    )

    # ==================== NOUVEAUX CHAMPS - TAGS ====================
    
    invoice_tag_ids = fields.Many2many(
        'lolirine.invoice.tag',
        'account_move_tag_rel',
        'move_id',
        'tag_id',
        string='Tags',
        help='Tags pour classifier la facture'
    )

    # ==================== NOUVEAUX CHAMPS - NOTES INTERNES ====================
    
    internal_note = fields.Text(
        string='Note interne',
        help='Note visible uniquement en interne, non imprimee sur la facture'
    )
    
    internal_note_important = fields.Boolean(
        string='Note importante',
        default=False,
        help='Marquer la note comme importante'
    )

    # ==================== NOUVEAUX CHAMPS - RELANCES ====================
    
    reminder_ids = fields.One2many(
        'lolirine.invoice.reminder',
        'invoice_id',
        string='Relances'
    )
    
    reminder_count = fields.Integer(
        string='Nb Relances',
        compute='_compute_reminder_count',
        store=True
    )
    
    last_reminder_date = fields.Date(
        string='Derniere relance',
        compute='_compute_last_reminder',
        store=True
    )
    
    last_reminder_type = fields.Selection([
        ('reminder_1', '1er Rappel'),
        ('reminder_2', '2eme Rappel'),
        ('reminder_3', '3eme Rappel'),
        ('formal_notice', 'Mise en demeure'),
        ('lawyer', 'Transmission avocat'),
    ], string='Dernier type relance', compute='_compute_last_reminder', store=True)
    
    next_reminder_date = fields.Date(
        string='Prochaine relance',
        compute='_compute_next_reminder'
    )
    
    reminder_status = fields.Selection([
        ('none', 'Aucune'),
        ('reminder_1', '1er Rappel'),
        ('reminder_2', '2eme Rappel'),
        ('reminder_3', '3eme Rappel'),
        ('formal_notice', 'Mise en demeure'),
        ('lawyer', 'Avocat'),
    ], string='Statut relance', compute='_compute_reminder_status', store=True)

    # ==================== NOUVEAUX CHAMPS - ECHEANCES ====================
    
    days_until_due = fields.Integer(
        string='Jours avant echeance',
        compute='_compute_days_until_due'
    )
    
    days_overdue = fields.Integer(
        string='Jours de retard',
        compute='_compute_days_overdue',
        store=True
    )
    
    is_overdue = fields.Boolean(
        string='En retard',
        compute='_compute_is_overdue',
        store=True
    )
    
    overdue_level = fields.Selection([
        ('ok', 'A jour'),
        ('warning', 'Bientot du'),
        ('danger', 'En retard'),
        ('critical', 'Critique'),
    ], string='Niveau urgence', compute='_compute_overdue_level', store=True)

    # ==================== NOUVEAUX CHAMPS - PENALITES ====================
    
    penalty_amount = fields.Monetary(
        string='Penalites de retard',
        compute='_compute_penalty_amount',
        help='Penalites calculees selon le taux legal belge (10.5%)'
    )
    
    total_with_penalty = fields.Monetary(
        string='Total avec penalites',
        compute='_compute_penalty_amount'
    )

    # ==================== NOUVEAUX CHAMPS - HISTORIQUE CLIENT ====================
    
    partner_invoice_count = fields.Integer(
        string='Factures client',
        compute='_compute_partner_invoice_count'
    )
    
    partner_unpaid_count = fields.Integer(
        string='Impayees client',
        compute='_compute_partner_invoice_count'
    )
    
    partner_total_due = fields.Monetary(
        string='Total du client',
        compute='_compute_partner_invoice_count'
    )

    # ==================== NOUVEAUX CHAMPS - REMBOURSEMENT ====================

    refund_payment_id = fields.Many2one(
        'account.payment',
        string='Paiement de remboursement',
        copy=False,
    )

    refund_state = fields.Selection([
        ('pending', 'Remboursement en attente'),
        ('done', 'Rembourse'),
    ], string='Etat remboursement',
       store=True,
       readonly=True,
       copy=False,
    )

    # ==================== COMPUTES ====================

    @api.depends('reminder_ids')
    def _compute_reminder_count(self):
        for move in self:
            move.reminder_count = len(move.reminder_ids.filtered(lambda r: r.state != 'cancelled'))

    @api.depends('reminder_ids.date', 'reminder_ids.reminder_type', 'reminder_ids.state')
    def _compute_last_reminder(self):
        for move in self:
            sent_reminders = move.reminder_ids.filtered(lambda r: r.state == 'sent')
            if sent_reminders:
                last = sent_reminders.sorted('date', reverse=True)[0]
                move.last_reminder_date = last.date
                move.last_reminder_type = last.reminder_type
            else:
                move.last_reminder_date = False
                move.last_reminder_type = False

    @api.depends('reminder_ids.state', 'reminder_ids.reminder_type', 'payment_state')
    def _compute_reminder_status(self):
        for move in self:
            if move.payment_state in ('paid', 'reversed'):
                move.reminder_status = 'none'
                continue
            active_reminders = move.reminder_ids.filtered(
                lambda r: r.state in ('draft', 'sent')
            )
            if active_reminders:
                type_order = ['reminder_1', 'reminder_2', 'reminder_3', 'formal_notice', 'lawyer']
                highest = 'reminder_1'
                for r in active_reminders:
                    if r.reminder_type in type_order:
                        if type_order.index(r.reminder_type) > type_order.index(highest):
                            highest = r.reminder_type
                move.reminder_status = highest
            else:
                move.reminder_status = 'none'

    def _compute_next_reminder(self):
        config = self.env['lolirine.invoice.reminder.config'].search([], limit=1)
        for move in self:
            if move.state != 'posted' or move.payment_state == 'paid':
                move.next_reminder_date = False
                continue
            if not move.invoice_date_due:
                move.next_reminder_date = False
                continue
            due_date = move.invoice_date_due
            if not move.last_reminder_type:
                days = config.reminder_1_days if config else 7
                move.next_reminder_date = due_date + timedelta(days=days)
            elif move.last_reminder_type == 'reminder_1':
                days = config.reminder_2_days if config else 14
                move.next_reminder_date = due_date + timedelta(days=days)
            elif move.last_reminder_type == 'reminder_2':
                days = config.reminder_3_days if config else 21
                move.next_reminder_date = due_date + timedelta(days=days)
            elif move.last_reminder_type == 'reminder_3':
                days = config.formal_notice_days if config else 30
                move.next_reminder_date = due_date + timedelta(days=days)
            else:
                move.next_reminder_date = False

    def _compute_days_until_due(self):
        today = fields.Date.today()
        for move in self:
            if move.invoice_date_due:
                delta = move.invoice_date_due - today
                move.days_until_due = delta.days
            else:
                move.days_until_due = 0

    @api.depends('invoice_date_due', 'payment_state')
    def _compute_days_overdue(self):
        today = fields.Date.today()
        for move in self:
            if move.invoice_date_due and move.payment_state not in ('paid', 'reversed'):
                delta = today - move.invoice_date_due
                move.days_overdue = max(0, delta.days)
            else:
                move.days_overdue = 0

    @api.depends('days_overdue', 'payment_state')
    def _compute_is_overdue(self):
        for move in self:
            move.is_overdue = move.days_overdue > 0 and move.payment_state not in ('paid', 'reversed')

    @api.depends('days_overdue', 'days_until_due', 'payment_state')
    def _compute_overdue_level(self):
        for move in self:
            if move.payment_state in ('paid', 'reversed'):
                move.overdue_level = 'ok'
            elif move.days_overdue > 30:
                move.overdue_level = 'critical'
            elif move.days_overdue > 0:
                move.overdue_level = 'danger'
            elif move.days_until_due <= 7:
                move.overdue_level = 'warning'
            else:
                move.overdue_level = 'ok'

    def _compute_penalty_amount(self):
        annual_rate = 0.105
        for move in self:
            if move.days_overdue > 0 and move.amount_residual > 0:
                move.penalty_amount = move.amount_residual * (annual_rate / 365) * move.days_overdue
                move.total_with_penalty = move.amount_residual + move.penalty_amount
            else:
                move.penalty_amount = 0.0
                move.total_with_penalty = move.amount_residual

    def _compute_partner_invoice_count(self):
        for move in self:
            if move.partner_id:
                invoices = self.search([
                    ('partner_id', '=', move.partner_id.id),
                    ('move_type', 'in', ('out_invoice', 'out_refund')),
                    ('state', '=', 'posted')
                ])
                move.partner_invoice_count = len(invoices)
                unpaid = invoices.filtered(lambda i: i.payment_state not in ('paid', 'reversed'))
                move.partner_unpaid_count = len(unpaid)
                move.partner_total_due = sum(unpaid.mapped('amount_residual'))
            else:
                move.partner_invoice_count = 0
                move.partner_unpaid_count = 0
                move.partner_total_due = 0.0

    # ==================== WARNINGS / CONTROLES ====================

    @api.onchange('invoice_date', 'journal_id')
    def _onchange_warn_invoice_date(self):
        if (
            self.journal_id.id == GARDE_MEUBLE_JOURNAL_ID
            and self.invoice_date
            and self.invoice_date.day != 20
        ):
            return {
                'warning': {
                    'title': 'Date inhabituelle',
                    'message': (
                        'La date de facturation est le %s, '
                        'alors que les factures garde-meuble sont normalement '
                        'generees le 20 du mois via le cron automatique.\n\n'
                        'Verifiez que cette creation est intentionnelle.'
                    ) % self.invoice_date.strftime('%d/%m/%Y'),
                }
            }

    # ==================== ACTIONS EXISTANTES ====================

    def action_post(self):
        """Override pour envoyer automatiquement la facture apres confirmation"""
        # Warning chatter si facture garde-meuble creee manuellement
        for move in self:
            if (
                move.journal_id.id == GARDE_MEUBLE_JOURNAL_ID
                and move.move_type == 'out_invoice'
                and not move.invoice_origin
                and not self.env.context.get('cron_invoice')
            ):
                move.message_post(
                    body=(
                        '⚠️ <b>Facture créée manuellement</b> — '
                        'cette facture n\'est pas issue du cron de facturation automatique. '
                        'Date : %s. Utilisateur : %s.'
                    ) % (
                        move.invoice_date or 'non définie',
                        self.env.user.name,
                    ),
                    message_type='notification',
                )

        res = super().action_post()
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                if move.auto_send_invoice and not move.auto_send_peppol:
                    move._send_invoice_auto()
                elif move.auto_send_peppol:
                    move._send_invoice_peppol_auto()
        return res

    def _send_invoice_auto(self):
        """Envoyer la facture automatiquement par email avec PDF Lolirine attache"""
        self.ensure_one()
        import base64
        
        if not self.partner_id.email:
            self.message_post(
                body="Envoi automatique impossible : le client n'a pas d'adresse email configuree.",
                message_type='notification'
            )
            return False
        
        try:
            report = self.env.ref('lolirine_invoice.action_report_invoice_lolirine', raise_if_not_found=False)
            if not report:
                report = self.env.ref('account.account_invoices', raise_if_not_found=False)
            
            attachment_ids = []
            if report:
                pdf_content, _unused = report._render_qweb_pdf(report.id, [self.id])
                attachment = self.env['ir.attachment'].create({
                    'name': f"Facture_{self.name.replace('/', '_')}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'account.move',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                attachment_ids.append(attachment.id)
            
            body_html = f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p>Bonjour {self.partner_id.name},</p>
    <p>Veuillez trouver en piece jointe votre facture mensuelle.</p>
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%; max-width: 400px;">
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Numero de facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.name}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date de facturation</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_date or ''}</td>
        </tr>
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Date d'echeance</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_date_due or ''}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant total</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>{self.amount_total:.2f} EUR</strong></td>
        </tr>
    </table>
    <p><strong>Modalites de paiement :</strong></p>
    <ul>
        <li>Communication structuree : {self.payment_reference or 'Voir facture'}</li>
        <li>Compte bancaire : BE07 7320 5208 0866 - CBC</li>
    </ul>
    <p>Cordialement,<br/><strong>Lolirine Garde-Meubles</strong><br/>Feron Rodney<br/>Tel. : 0497/44 41 46</p>
</div>
            """
            
            mail = self.env['mail.mail'].sudo().create({
                'subject': f"Envoi de votre facture mensuelle {self.name} - Garde-meubles Lolirine",
                'body_html': body_html,
                'email_from': 'Srl Lolirine <gardemeublelolirine@gmail.com>',
                'email_to': self.partner_id.email,
                'model': 'account.move',
                'res_id': self.id,
                'attachment_ids': [(6, 0, attachment_ids)],
            })
            mail.send()
            self.write({'is_move_sent': True})
            self.message_post(
                body=f"Facture envoyee automatiquement par email a {self.partner_id.email}.",
                attachment_ids=attachment_ids,
                message_type='notification'
            )
            return True
            
        except Exception as e:
            _logger.error("Erreur envoi facture %s: %s", self.name, str(e))
            self.message_post(
                body=f"Erreur lors de l'envoi automatique : {str(e)}",
                message_type='notification'
            )
            return False

    def _send_invoice_peppol_auto(self):
        self.ensure_one()
        if not self.partner_id.peppol_eas or not self.partner_id.peppol_endpoint:
            self.message_post(
                body=_("Envoi Peppol impossible : le client n'a pas d'identifiant Peppol configure."),
                message_type='notification'
            )
            return False
        try:
            wizard = self.env['account.move.send.wizard'].with_context(
                active_model='account.move',
                active_ids=self.ids,
            ).create({})
            wizard.action_send_and_print()
            self.message_post(
                body=_("Facture envoyee automatiquement via Peppol a %s (EAS: %s)") % (
                    self.partner_id.peppol_endpoint,
                    self.partner_id.peppol_eas,
                ),
                message_type='notification'
            )
            return True
        except Exception as e:
            _logger.error("Erreur envoi Peppol pour facture %s: %s", self.name, str(e))
            self.message_post(
                body=_("Erreur lors de l'envoi Peppol automatique : %s") % str(e),
                message_type='notification'
            )
            return False

    def action_send_peppol(self):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_("La facture doit etre confirmee avant d'etre envoyee via Peppol."))
        if not self.partner_id.peppol_eas or not self.partner_id.peppol_endpoint:
            raise UserError(_("Le client n'a pas d'identifiant Peppol configure."))
        try:
            wizard = self.env['account.move.send.wizard'].with_context(
                active_model='account.move',
                active_ids=self.ids,
            ).create({})
            wizard.action_send_and_print()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succes'),
                    'message': _('Facture envoyee via Peppol a %s') % self.partner_id.peppol_endpoint,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_("Erreur lors de l'envoi Peppol : %s") % str(e))

    def action_preview_invoice(self):
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/lolirine_invoice.report_invoice_lolirine/%s' % self.id,
            'target': 'new',
        }

    def action_preview_invoice_html(self):
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
                'url': '/report/html/lolirine_invoice.report_invoice_lolirine/%s' % self.id,
                'target': 'new',
            }

    def action_confirm_and_send(self):
        self.ensure_one()
        if self.state == 'draft':
            self.action_post()
        return self.action_open_send_wizard()

    def action_open_send_wizard(self):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_("La facture doit etre confirmee avant d'etre envoyee."))
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
        self.ensure_one()
        if self.state != 'posted':
            raise UserError("La facture doit etre confirmee avant d'etre envoyee.")
        template = self.env.ref('lolirine_invoice.email_template_invoice', raise_if_not_found=False)
        if not template:
            template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        if not template:
            raise UserError("Aucun template d'email trouve.")
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=False)
        ctx = {
            'default_model': 'account.move',
            'default_res_ids': self.ids,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'mark_invoice_as_sent': True,
            'force_email': True,
        }
        return {
            'name': 'Envoyer la facture par email',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    # ==================== NOUVELLES ACTIONS ====================

    def action_create_reminder(self):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_("La facture doit etre confirmee."))
        if self.payment_state == 'paid':
            raise UserError(_("Cette facture est deja payee."))
        if not self.last_reminder_type:
            next_type = 'reminder_1'
        elif self.last_reminder_type == 'reminder_1':
            next_type = 'reminder_2'
        elif self.last_reminder_type == 'reminder_2':
            next_type = 'reminder_3'
        elif self.last_reminder_type == 'reminder_3':
            next_type = 'formal_notice'
        else:
            next_type = 'lawyer'
        return {
            'name': _('Nouvelle relance'),
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.invoice.reminder',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_reminder_type': next_type,
            },
        }

    def action_view_reminders(self):
        self.ensure_one()
        return {
            'name': _('Relances'),
            'type': 'ir.actions.act_window',
            'res_model': 'lolirine.invoice.reminder',
            'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {'default_invoice_id': self.id},
        }

    def action_view_partner_invoices(self):
        self.ensure_one()
        return {
            'name': _('Factures de %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
            ],
            'context': {'default_partner_id': self.partner_id.id},
        }

    def action_view_partner_unpaid(self):
        self.ensure_one()
        return {
            'name': _('Impayees de %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
                ('payment_state', 'not in', ('paid', 'reversed')),
            ],
        }

    def action_smart_duplicate(self):
        self.ensure_one()
        new_invoice = self.copy({
            'invoice_date': fields.Date.today(),
            'date': fields.Date.today(),
            'invoice_tag_ids': [(6, 0, self.invoice_tag_ids.ids)],
            'internal_note': self.internal_note,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle facture'),
            'res_model': 'account.move',
            'res_id': new_invoice.id,
            'view_mode': 'form',
            'context': {'default_move_type': self.move_type},
        }

    def action_write_off_rounding(self):
        self.ensure_one()
        if self.amount_residual > 0.05:
            raise UserError(
                _("Le solde residuel (%.2f EUR) est trop eleve pour un apurement automatique.") % self.amount_residual
            )
        rounding_account = self.env['account.account'].search(
            [('code', '=', '657100')], limit=1
        )
        if not rounding_account:
            raise UserError(_("Compte 657100 (Differences de paiement) introuvable."))
        misc_journal = self.env['account.journal'].search(
            [('code', '=', 'MISC')], limit=1
        )
        receivable_account = self.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
        )[0].account_id
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': date.today(),
            'journal_id': misc_journal.id,
            'ref': 'Apurement arrondi %s' % self.name,
            'line_ids': [
                (0, 0, {
                    'account_id': rounding_account.id,
                    'debit': self.amount_residual,
                    'credit': 0.0,
                    'name': 'Difference arrondi %s' % self.name,
                    'partner_id': self.partner_id.id,
                }),
                (0, 0, {
                    'account_id': receivable_account.id,
                    'debit': 0.0,
                    'credit': self.amount_residual,
                    'name': 'Apurement arrondi %s' % self.name,
                    'partner_id': self.partner_id.id,
                }),
            ],
        })
        move.action_post()
        inv_line = self.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
                      and not l.reconciled
        )
        write_off_line = move.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
                      and not l.reconciled
        )
        (inv_line + write_off_line).reconcile()
        self.message_post(
            body=_("Arrondi de %(amount)s EUR apure sur 657100 (%(move)s)",
                   amount=self.amount_residual, move=move.name)
        )
        return True

    def action_view_refund_payments(self):
        self.ensure_one()
        if not self.refund_payment_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': 'Paiement de remboursement',
            'res_model': 'account.payment',
            'res_id': self.refund_payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    auto_send_invoice = fields.Boolean(
        string="Envoi auto factures email",
        default=False,
        help="Si active, les factures de ce client seront envoyees automatiquement par email"
    )
    
    auto_send_peppol = fields.Boolean(
        string="Envoi auto factures Peppol",
        default=False,
        help="Si active, les factures de ce client seront envoyees automatiquement via Peppol"
    )
    
    invoice_overdue_count = fields.Integer(
        string='Factures en retard',
        compute='_compute_invoice_stats'
    )
    invoice_overdue_amount = fields.Monetary(
        string='Montant en retard',
        compute='_compute_invoice_stats'
    )
    
    @api.onchange('vat')
    def _onchange_vat_peppol(self):
        if self.vat and not self.peppol_endpoint:
            vat_clean = self.vat.replace(' ', '').replace('.', '')
            if vat_clean.startswith('BE'):
                self.peppol_eas = '0208'
                self.peppol_endpoint = vat_clean[2:]

    def _compute_invoice_stats(self):
        for partner in self:
            overdue = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
                ('payment_state', 'not in', ('paid', 'reversed')),
                ('is_overdue', '=', True),
            ])
            partner.invoice_overdue_count = len(overdue)
            partner.invoice_overdue_amount = sum(overdue.mapped('amount_residual'))


class SaleSubscription(models.Model):
    _inherit = "sale.order"
    
    auto_send_peppol = fields.Boolean(
        string="Envoi auto Peppol",
        default=False,
        help="Si active, les factures generees seront envoyees automatiquement via Peppol"
    )
    
    @api.onchange('partner_id')
    def _onchange_partner_peppol(self):
        if self.partner_id and self.partner_id.auto_send_peppol:
            self.auto_send_peppol = True
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        for move in moves:
            if move.partner_id.auto_send_invoice:
                move.auto_send_invoice = True
            subscription = self.filtered(lambda s: move.partner_id in s.partner_id)
            if subscription and subscription[0].auto_send_peppol:
                move.auto_send_peppol = True
            elif move.partner_id.auto_send_peppol:
                move.auto_send_peppol = True
        return moves

    def set_close(self, close_reason_id=None, renew=False, **kwargs):
        for subscription in self:
            if hasattr(subscription, 'is_subscription') and not subscription.is_subscription:
                continue
        
            vals = {'subscription_state': '6_churn'}
            if close_reason_id:
                vals['close_reason_id'] = close_reason_id
            subscription.write(vals)
        
            # IMPORTANT : forcer next_invoice_date / recurring_next_date à False
            # APRÈS le write subscription_state, sinon le compute Odoo
            # _compute_next_invoice_date les recalcule depuis start_date.
            post_close_vals = {}
            if 'next_invoice_date' in subscription._fields:
            post_close_vals['next_invoice_date'] = False
            if 'recurring_next_date' in subscription._fields:
                post_close_vals['recurring_next_date'] = False
            if 'end_date' in subscription._fields and not subscription.end_date:
                post_close_vals['end_date'] = fields.Date.today()
            if post_close_vals:
                subscription.write(post_close_vals)
        
            msg = "Abonnement clôturé."
            if close_reason_id:
                try:
                    reason = self.env['sale.order.close.reason'].browse(close_reason_id)
                    if reason.exists():
                        msg = "Abonnement clôturé. Raison : %s" % reason.name
                except Exception:
                    pass
        
            subscription.message_post(
                body=msg,
                message_type='notification',
                subtype_xmlid='mail.mt_note',  # note interne — pas de notif aux followers
            )
            _logger.info("Abonnement %s clôturé via patch set_close()", subscription.name)
        return True
