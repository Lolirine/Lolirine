# -*- coding: utf-8 -*-

import base64
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InvoiceReminder(models.Model):
    _name = 'lolirine.invoice.reminder'
    _description = 'Relance facture'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=True,
        ondelete='cascade',
        domain=[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
        tracking=True
    )
    
    partner_id = fields.Many2one(related='invoice_id.partner_id', string='Client', store=True)
    
    reminder_type = fields.Selection([
        ('reminder_1', '1er Rappel'),
        ('reminder_2', '2eme Rappel'),
        ('reminder_3', '3eme Rappel'),
        ('formal_notice', 'Mise en demeure'),
    ], string='Type de relance', required=True, default='reminder_1', tracking=True)
    
    date = fields.Date(string='Date', default=fields.Date.today, required=True, tracking=True)
    send_date = fields.Datetime(string='Date envoi', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyee'),
        ('paid', 'Payee'),
        ('cancelled', 'Annulee'),
    ], string='Etat', default='draft', tracking=True)
    
    amount_due = fields.Monetary(related='invoice_id.amount_residual', string='Montant du', store=True)
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    
    days_overdue = fields.Integer(string='Jours de retard', compute='_compute_days_overdue', store=True)
    
    penalty_amount = fields.Monetary(string='Penalites', compute='_compute_penalty_amount', store=True)
    total_due = fields.Monetary(string='Total du', compute='_compute_penalty_amount', store=True)
    
    notes = fields.Text(string='Notes internes')
    email_sent = fields.Boolean(string='Email envoye', default=False)
    auto_generated = fields.Boolean(string='Auto-genere', default=False)
    company_id = fields.Many2one(related='invoice_id.company_id', store=True)

    @api.depends('invoice_id', 'reminder_type')
    def _compute_name(self):
        type_names = {'reminder_1': 'R1', 'reminder_2': 'R2', 'reminder_3': 'R3', 'formal_notice': 'MED'}
        for rec in self:
            if rec.invoice_id and rec.reminder_type:
                rec.name = f"{type_names.get(rec.reminder_type, 'REL')}/{rec.invoice_id.name}"
            else:
                rec.name = 'Nouvelle relance'

    @api.depends('invoice_id.invoice_date_due')
    def _compute_days_overdue(self):
        today = fields.Date.today()
        for rec in self:
            if rec.invoice_id and rec.invoice_id.invoice_date_due:
                delta = today - rec.invoice_id.invoice_date_due
                rec.days_overdue = max(0, delta.days)
            else:
                rec.days_overdue = 0

    @api.depends('amount_due', 'days_overdue')
    def _compute_penalty_amount(self):
        config = self.env['lolirine.invoice.reminder.config'].search([], limit=1)
        annual_rate = config.penalty_rate / 100 if config else 0.105
        for rec in self:
            if rec.days_overdue > 0 and rec.amount_due > 0:
                rec.penalty_amount = rec.amount_due * (annual_rate / 365) * rec.days_overdue
                rec.total_due = rec.amount_due + rec.penalty_amount
            else:
                rec.penalty_amount = 0.0
                rec.total_due = rec.amount_due or 0.0

    def _get_email_subject(self):
        self.ensure_one()
        subjects = {
            'reminder_1': f"Rappel de paiement - Facture {self.invoice_id.name}",
            'reminder_2': f"2eme Rappel - Facture {self.invoice_id.name}",
            'reminder_3': f"URGENT - 3eme Rappel - Facture {self.invoice_id.name}",
            'formal_notice': f"MISE EN DEMEURE - Facture {self.invoice_id.name}",
        }
        return subjects.get(self.reminder_type, f"Relance - Facture {self.invoice_id.name}")

    def _get_email_body(self):
        self.ensure_one()
        return f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p>Bonjour {self.partner_id.name or ''},</p>
    
    <p>Sauf erreur de notre part, nous n'avons pas encore recu le paiement de la facture suivante :</p>
    
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%; max-width: 400px;">
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.name}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Echeance</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.invoice_date_due or ''}</td>
        </tr>
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>{self.amount_due:.2f} EUR</strong></td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Retard</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.days_overdue} jours</td>
        </tr>
    </table>
    
    <p><strong>Paiement :</strong></p>
    <ul>
        <li>Communication : {self.invoice_id.payment_reference or self.invoice_id.name}</li>
        <li>IBAN : BE07 7320 5208 0866 - CBC</li>
    </ul>
    
    <p>Cordialement,</p>
    <p><strong>Lolirine Garde-Meubles</strong><br/>Tel : 0497/44 41 46</p>
</div>
"""

    def action_send_reminder(self):
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError("Le client n'a pas d'adresse email.")
        self._send_reminder_email()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Relance envoyee',
                'message': f'Email envoye a {self.partner_id.email}',
                'type': 'success',
                'sticky': False,
            }
        }

    def _send_reminder_email(self):
        self.ensure_one()
        if not self.partner_id.email:
            return False
        
        report = self.env.ref('lolirine_invoice.action_report_invoice_lolirine', raise_if_not_found=False)
        if not report:
            report = self.env.ref('account.account_invoices', raise_if_not_found=False)
        
        attachment_ids = []
        if report:
            try:
                pdf_content, _ = report._render_qweb_pdf(report.id, [self.invoice_id.id])
                attachment = self.env['ir.attachment'].create({
                    'name': f"{self.invoice_id.name.replace('/', '_')}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'lolirine.invoice.reminder',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                attachment_ids.append(attachment.id)
            except Exception as e:
                _logger.error(f"Erreur PDF: {e}")
        
        mail = self.env['mail.mail'].sudo().create({
            'subject': self._get_email_subject(),
            'body_html': self._get_email_body(),
            'email_from': 'gardemeublelolirine@gmail.com',
            'email_to': self.partner_id.email,
            'model': 'lolirine.invoice.reminder',
            'res_id': self.id,
            'attachment_ids': [(6, 0, attachment_ids)],
        })
        mail.send()
        
        self.write({'state': 'sent', 'send_date': fields.Datetime.now(), 'email_sent': True})
        self.message_post(body=f"Relance envoyee a {self.partner_id.email}", message_type='notification')
        return True

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'send_date': False, 'email_sent': False})

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }

    def action_create_next_reminder(self):
        self.ensure_one()
        next_type = {'reminder_1': 'reminder_2', 'reminder_2': 'reminder_3', 'reminder_3': 'formal_notice'}.get(self.reminder_type)
        if not next_type:
            raise UserError("Pas de relance suivante disponible.")
        existing = self.search([('invoice_id', '=', self.invoice_id.id), ('reminder_type', '=', next_type), ('state', '!=', 'cancelled')], limit=1)
        if existing:
            raise UserError("Une relance de ce type existe deja.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle relance',
            'res_model': 'lolirine.invoice.reminder',
            'view_mode': 'form',
            'context': {'default_invoice_id': self.invoice_id.id, 'default_reminder_type': next_type},
        }

    @api.model
    def _cron_auto_reminder(self):
        config = self.env['lolirine.invoice.reminder.config'].search([('auto_reminder', '=', True)], limit=1)
        if not config:
            return
        
        today = fields.Date.today()
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('partner_id.email', '!=', False),
        ])
        
        created = sent = 0
        for inv in invoices:
            days = (today - inv.invoice_date_due).days
            rtype = None
            if days >= config.formal_notice_days:
                rtype = 'formal_notice'
            elif days >= config.reminder_3_days:
                rtype = 'reminder_3'
            elif days >= config.reminder_2_days:
                rtype = 'reminder_2'
            elif days >= config.reminder_1_days:
                rtype = 'reminder_1'
            
            if not rtype:
                continue
            
            if self.search([('invoice_id', '=', inv.id), ('reminder_type', '=', rtype), ('state', '!=', 'cancelled')], limit=1):
                continue
            
            if rtype != 'reminder_1':
                prev = {'reminder_2': 'reminder_1', 'reminder_3': 'reminder_2', 'formal_notice': 'reminder_3'}.get(rtype)
                if not self.search([('invoice_id', '=', inv.id), ('reminder_type', '=', prev), ('state', '=', 'sent')], limit=1):
                    continue
            
            try:
                reminder = self.create({'invoice_id': inv.id, 'reminder_type': rtype, 'auto_generated': True})
                created += 1
                if reminder._send_reminder_email():
                    sent += 1
            except Exception as e:
                _logger.error(f"Erreur auto-relance: {e}")
        
        _logger.info(f"Auto-relance: {created} creees, {sent} envoyees")
        return {'created': created, 'sent': sent}

    @api.model
    def _cron_check_paid(self):
        for r in self.search([('state', 'in', ['draft', 'sent']), ('invoice_id.payment_state', '=', 'paid')]):
            r.write({'state': 'paid'})
            r.message_post(body="Facture payee - cloture auto", message_type='notification')


class InvoiceReminderConfig(models.Model):
    _name = 'lolirine.invoice.reminder.config'
    _description = 'Configuration relances'

    name = fields.Char(default='Configuration')
    reminder_1_days = fields.Integer(string='1er rappel (jours)', default=7)
    reminder_2_days = fields.Integer(string='2eme rappel (jours)', default=14)
    reminder_3_days = fields.Integer(string='3eme rappel (jours)', default=21)
    formal_notice_days = fields.Integer(string='Mise en demeure (jours)', default=30)
    penalty_rate = fields.Float(string='Taux penalite (%)', default=10.5)
    auto_reminder = fields.Boolean(string='Auto-relance active', default=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def action_test_auto_reminder(self):
        result = self.env['lolirine.invoice.reminder']._cron_auto_reminder()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test termine',
                'message': f"Creees: {result.get('created', 0)}, Envoyees: {result.get('sent', 0)}",
                'type': 'success',
                'sticky': True,
            }
        }
        
