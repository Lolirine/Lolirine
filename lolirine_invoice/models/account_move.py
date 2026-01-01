# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


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

    def _compute_next_reminder(self):
        """Calcule la date de la prochaine relance recommandee"""
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
                # Pas encore de relance -> 1er rappel
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
        """Calcul penalites selon taux legal belge"""
        annual_rate = 0.105  # 10.5% taux 2024
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

    # ==================== ACTIONS EXISTANTES ====================

    def action_post(self):
        """Override pour envoyer automatiquement la facture apres confirmation"""
        res = super().action_post()
        
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                if move.auto_send_invoice:
                    move._send_invoice_auto()
                if move.auto_send_peppol:
                    move._send_invoice_peppol_auto()
        
        return res

    def _send_invoice_auto(self):
        """Envoyer la facture automatiquement par email"""
        self.ensure_one()
        
        if not self.partner_id.email:
            self.message_post(
                body=_("Envoi automatique impossible : le client n'a pas d'adresse email configuree."),
                message_type='notification'
            )
            return False
        
        template = self.env.ref('lolirine_invoice.email_template_invoice', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.write({'is_move_sent': True})
            self.message_post(
                body=_("Facture envoyee automatiquement par email a %s") % self.partner_id.email,
                message_type='notification'
            )
            return True
        return False

    def _send_invoice_peppol_auto(self):
        """Envoyer la facture automatiquement via Peppol"""
        self.ensure_one()
        
        if not self.partner_id.peppol_eas or not self.partner_id.peppol_endpoint:
            self.message_post(
                body=_("Envoi Peppol impossible : le client n'a pas d'identifiant Peppol configure."),
                message_type='notification'
            )
            return False
        
        try:
            if hasattr(self, 'edi_document_ids'):
                peppol_format = self.env['account.edi.format'].search([
                    ('code', 'in', ['peppol', 'ubl_bis3', 'facturx', 'ubl_2_1'])
                ], limit=1)
                
                if peppol_format:
                    self._process_edi_web_services(peppol_format)
                    self.write({
                        'peppol_sent': True,
                        'peppol_sent_date': fields.Datetime.now()
                    })
                    self.message_post(
                        body=_("Facture envoyee automatiquement via Peppol a %s") % self.partner_id.peppol_endpoint,
                        message_type='notification'
                    )
                    return True
            
            if hasattr(self, 'action_process_edi_web_services'):
                self.action_process_edi_web_services()
                self.write({
                    'peppol_sent': True,
                    'peppol_sent_date': fields.Datetime.now()
                })
                self.message_post(
                    body=_("Facture envoyee via Peppol a %s") % self.partner_id.peppol_endpoint,
                    message_type='notification'
                )
                return True
                
            self.message_post(
                body=_("Module EDI Peppol non configure."),
                message_type='notification'
            )
            return False
            
        except Exception as e:
            _logger.error("Erreur envoi Peppol pour facture %s: %s", self.name, str(e))
            self.message_post(
                body=_("Erreur lors de l'envoi Peppol : %s") % str(e),
                message_type='notification'
            )
            return False

    def action_send_peppol(self):
        """Action manuelle pour envoyer via Peppol"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit etre confirmee avant d'etre envoyee via Peppol."))
        
        if not self.partner_id.peppol_eas or not self.partner_id.peppol_endpoint:
            raise UserError(_("Le client n'a pas d'identifiant Peppol configure."))
        
        result = self._send_invoice_peppol_auto()
        
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succes'),
                    'message': _('Facture envoyee via Peppol'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Attention'),
                    'message': _('Verifiez le chatter pour les details'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

    def action_preview_invoice(self):
        """Ouvrir un apercu de la facture"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/lolirine_invoice.report_invoice_lolirine/%s' % self.id,
            'target': 'new',
        }

    def action_preview_invoice_html(self):
        """Ouvrir un apercu HTML de la facture"""
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
        """Confirmer la facture et ouvrir le wizard d'envoi"""
        self.ensure_one()
        
        if self.state == 'draft':
            self.action_post()
        
        return self.action_open_send_wizard()

    def action_open_send_wizard(self):
        """Ouvrir le wizard d'envoi de facture"""
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
        """Envoyer la facture par email directement"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit etre confirmee avant d'etre envoyee."))
        
        template = self.env.ref('lolirine_invoice.email_template_invoice', raise_if_not_found=False)
        if not template:
            raise UserError(_("Le template d'email n'a pas ete trouve."))
        
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
            'name': _('Envoyer la facture par email'),
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
        """Creer une nouvelle relance"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_("La facture doit etre confirmee."))
        
        if self.payment_state == 'paid':
            raise UserError(_("Cette facture est deja payee."))
        
        # Determiner le type de relance suivant
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
        """Voir les relances de la facture"""
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
        """Voir toutes les factures du client"""
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
        """Voir les factures impayees du client"""
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
        """Duplication intelligente avec mise a jour des dates"""
        self.ensure_one()
        
        # Copier la facture
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
    
    peppol_eas = fields.Selection([
        ('0002', '0002 - SIREN'),
        ('0007', '0007 - Numero TVA'),
        ('0009', '0009 - SIRET'),
        ('0088', '0088 - EAN Location Code'),
        ('0130', '0130 - EU VAT'),
        ('0208', '0208 - BE:EN'),
        ('9930', '9930 - BE:VAT'),
    ], string="EAS (Scheme ID)", 
       help="Electronic Address Scheme pour Peppol. Pour la Belgique, utilisez 0208 (BE:EN).")
    
    peppol_endpoint = fields.Char(
        string="Endpoint Peppol",
        help="Identifiant Peppol (ex: numero d'entreprise pour BE:EN)"
    )
    
    # Statistiques factures
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
        """Suggerer l'endpoint Peppol base sur le numero TVA"""
        try:
            if self.vat and not self.peppol_endpoint:
                vat_clean = self.vat.replace(' ', '').replace('.', '')
                if vat_clean.startswith('BE'):
                    self.peppol_eas = '0208'
                    self.peppol_endpoint = vat_clean[2:]
        except (ValueError, Exception):
            # Ignorer les erreurs de validation Peppol (cache non rafraîchi)
            pass

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
        """Heriter les preferences Peppol du client"""
        if self.partner_id and self.partner_id.auto_send_peppol:
            self.auto_send_peppol = True
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        """Override pour propager l'option d'envoi auto"""
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
