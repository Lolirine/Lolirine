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
    
    reminder_fee = fields.Monetary(string='Frais de rappel', default=0.0)
    total_due = fields.Monetary(string='Total du', compute='_compute_total_due', store=True)
    
    notes = fields.Text(string='Notes internes')
    email_sent = fields.Boolean(string='Email envoye', default=False)
    auto_generated = fields.Boolean(string='Auto-genere', default=False)
    fee_added = fields.Boolean(string='Frais ajoutes', default=False)
    fee_invoice_id = fields.Many2one('account.move', string='Facture frais')
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

    @api.depends('amount_due', 'reminder_fee')
    def _compute_total_due(self):
        for rec in self:
            rec.total_due = (rec.amount_due or 0.0) + (rec.reminder_fee or 0.0)

    def _add_fee_to_invoice(self, amount, description):
        """Cree une facture de frais de rappel"""
        self.ensure_one()
        if amount <= 0 or self.fee_added:
            return False
        
        invoice = self.invoice_id
        
        # Chercher un produit "Frais de rappel"
        product = self.env['product.product'].search([('default_code', '=', 'FRAIS_RAPPEL')], limit=1)
        if not product:
            product = self.env['product.product'].search([('name', 'ilike', 'frais de rappel')], limit=1)
        
        # Creer une facture pour les frais
        fee_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': invoice.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': fields.Date.today(),
            'ref': f"Frais - {invoice.name}",
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'quantity': 1,
                'price_unit': amount,
                'product_id': product.id if product else False,
            })],
        })
        fee_invoice.action_post()
        
        self.write({
            'fee_added': True,
            'reminder_fee': amount,
            'fee_invoice_id': fee_invoice.id,
        })
        self.message_post(body=f"Facture de frais creee: {fee_invoice.name} - {amount:.2f} EUR")
        
        _logger.info(f"Frais de rappel {amount} EUR - Facture {fee_invoice.name}")
        return fee_invoice

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
        
        fee_20 = 20.0 if self.reminder_type in ['reminder_3', 'formal_notice'] else 0.0
        fee_50 = 50.0 if self.reminder_type == 'formal_notice' else 0.0
        total_fees = fee_20 + fee_50
        total_due = self.amount_due + total_fees
        
        if self.reminder_type == 'reminder_1':
            warning = """
            <p style="background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107;">
                <strong>Attention :</strong> A defaut de paiement, des <strong>frais de rappel de 20 EUR</strong> pourront etre appliques conformement a nos conditions generales.
            </p>
            """
            amount_section = f"""
            <tr style="background-color: #f5f5f5;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>{self.amount_due:.2f} EUR</strong></td>
            </tr>
            """
        elif self.reminder_type == 'reminder_2':
            warning = """
            <p style="background-color: #f8d7da; padding: 10px; border-left: 4px solid #dc3545;">
                <strong>IMPORTANT :</strong> Sans paiement dans les <strong>5 jours</strong>, des <strong>frais de rappel de 20 EUR</strong> seront automatiquement ajoutes a votre facture.
            </p>
            """
            amount_section = f"""
            <tr style="background-color: #f5f5f5;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>{self.amount_due:.2f} EUR</strong></td>
            </tr>
            """
        elif self.reminder_type == 'reminder_3':
            warning = """
            <p style="background-color: #f8d7da; padding: 15px; border-left: 4px solid #dc3545;">
                <strong>DERNIER AVERTISSEMENT :</strong><br/><br/>
                Sans paiement dans les <strong>5 jours</strong> :<br/>
                - Des frais supplementaires de <strong>50 EUR</strong> seront appliques<br/>
                - Nous procederons a la <strong>rupture de votre contrat</strong> conformement a nos conditions generales
            </p>
            """
            amount_section = f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant facture</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{self.amount_due:.2f} EUR</td>
            </tr>
            <tr style="background-color: #fff3cd;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Frais de rappel</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">20,00 EUR</td>
            </tr>
            <tr style="background-color: #f5f5f5;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>TOTAL DU</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>{total_due:.2f} EUR</strong></td>
            </tr>
            """
        else:
            warning = """
            <p style="background-color: #f8d7da; padding: 15px; border-left: 4px solid #dc3545;">
                <strong>A DEFAUT DE PAIEMENT :</strong><br/><br/>
                - Votre <strong>contrat de garde-meubles sera resilie</strong> avec effet immediat<br/>
                - Les biens stockes feront l'objet d'une <strong>retention</strong> jusqu'au paiement integral<br/>
                - Le dossier sera transmis a notre <strong>service contentieux</strong> pour recouvrement judiciaire
            </p>
            """
            amount_section = f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant facture</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{self.amount_due:.2f} EUR</td>
            </tr>
            <tr style="background-color: #fff3cd;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Frais de rappel</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">20,00 EUR</td>
            </tr>
            <tr style="background-color: #f8d7da;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Frais mise en demeure</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">50,00 EUR</td>
            </tr>
            <tr style="background-color: #ffebee;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>TOTAL DU</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong style="color: #c0392b; font-size: 16px;">{total_due:.2f} EUR</strong></td>
            </tr>
            """
        
        intro = 'Sauf erreur de notre part, nous navons pas encore recu le paiement de la facture suivante :' if self.reminder_type == 'reminder_1' else 'Malgre nos precedents rappels, la facture suivante reste impayee :'
        
        return f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
    <p>Bonjour {self.partner_id.name or ''},</p>
    
    <p>{intro}</p>
    
    <table style="margin: 20px 0; border-collapse: collapse; width: 100%; max-width: 400px;">
        <tr style="background-color: #f5f5f5;">
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Facture</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.name}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Echeance</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{self.invoice_id.invoice_date_due or ''}</td>
        </tr>
        {amount_section}
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Retard</strong></td>
            <td style="padding: 10px; border: 1px solid #ddd; color: #c0392b;">{self.days_overdue} jours</td>
        </tr>
    </table>
    
    {warning}
    
    <p><strong>Coordonnees bancaires :</strong></p>
    <ul>
        <li>IBAN : BE07 7320 5208 0866 - CBC</li>
        <li>Communication : {self.invoice_id.payment_reference or self.invoice_id.name}</li>
    </ul>
    
    <p>Cordialement,</p>
    <p><strong>Lolirine Garde-Meubles</strong><br/>Tel : 0497/44 41 46</p>
</div>
"""

    def action_send_reminder(self):
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError("Le client n'a pas d'adresse email.")
        
        # Ajouter les frais si necessaire
        if self.reminder_type == 'reminder_3' and not self.fee_added:
            self._add_fee_to_invoice(20.0, f"Frais de rappel - {self.invoice_id.name}")
        elif self.reminder_type == 'formal_notice' and not self.fee_added:
            self._add_fee_to_invoice(50.0, f"Frais de mise en demeure - {self.invoice_id.name}")
        
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
    def _cron_auto_reminder(self, test_mode=False):
        """
        Cron job pour les relances automatiques
        
        Args:
            test_mode (bool): Si True, simule sans creer ni envoyer (dry run)
        
        Returns:
            dict: Resultat avec compteurs et details
        """
        config = self.env['lolirine.invoice.reminder.config'].search([('auto_reminder', '=', True)], limit=1)
        if not config:
            return {'created': 0, 'sent': 0, 'test_mode': test_mode, 'details': [], 'message': 'Auto-relance non activee dans la configuration'}
        
        today = fields.Date.today()
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('partner_id.email', '!=', False),
        ])
        
        created = sent = 0
        details = []  # Pour le mode test
        
        type_labels = {
            'reminder_1': '1er Rappel',
            'reminder_2': '2eme Rappel',
            'reminder_3': '3eme Rappel (+20 EUR)',
            'formal_notice': 'Mise en demeure (+50 EUR)',
        }
        
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
            
            # Verifier si relance existe deja
            if self.search([('invoice_id', '=', inv.id), ('reminder_type', '=', rtype), ('state', '!=', 'cancelled')], limit=1):
                continue
            
            # Verifier que la relance precedente a ete envoyee
            if rtype != 'reminder_1':
                prev = {'reminder_2': 'reminder_1', 'reminder_3': 'reminder_2', 'formal_notice': 'reminder_3'}.get(rtype)
                if not self.search([('invoice_id', '=', inv.id), ('reminder_type', '=', prev), ('state', '=', 'sent')], limit=1):
                    continue
            
            # Mode test : on enregistre ce qui serait fait sans le faire
            if test_mode:
                fee = 0
                if rtype == 'reminder_3':
                    fee = config.fee_reminder_3 or 20
                elif rtype == 'formal_notice':
                    fee = config.fee_formal_notice or 50
                    
                details.append({
                    'invoice_id': inv.id,
                    'partner_id': inv.partner_id.id,
                    'invoice': inv.name,
                    'partner': inv.partner_id.name,
                    'email': inv.partner_id.email,
                    'amount_due': inv.amount_residual,
                    'days_overdue': days,
                    'reminder_type': type_labels.get(rtype, rtype),
                    'fee': fee,
                })
                created += 1
                sent += 1
                continue
            
            # Mode reel : creer et envoyer
            try:
                reminder = self.create({'invoice_id': inv.id, 'reminder_type': rtype, 'auto_generated': True})
                created += 1
                
                # Ajouter frais si necessaire
                if rtype == 'reminder_3':
                    reminder._add_fee_to_invoice(config.fee_reminder_3 or 20.0, f"Frais de rappel - {inv.name}")
                elif rtype == 'formal_notice':
                    reminder._add_fee_to_invoice(config.fee_formal_notice or 50.0, f"Frais de mise en demeure - {inv.name}")
                
                if reminder._send_reminder_email():
                    sent += 1
            except Exception as e:
                _logger.error(f"Erreur auto-relance: {e}")
        
        result = {
            'created': created,
            'sent': sent,
            'test_mode': test_mode,
            'details': details,
        }
        
        if test_mode:
            _logger.info(f"[TEST MODE] Auto-relance: {created} seraient creees et envoyees")
        else:
            _logger.info(f"Auto-relance: {created} creees, {sent} envoyees")
        
        return result

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
    fee_reminder_3 = fields.Float(string='Frais 3eme rappel (EUR)', default=20.0)
    fee_formal_notice = fields.Float(string='Frais mise en demeure (EUR)', default=50.0)
    auto_reminder = fields.Boolean(string='Auto-relance active', default=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def action_test_auto_reminder(self):
        """Execute les relances automatiques (MODE REEL - envoie des emails!)"""
        result = self.env['lolirine.invoice.reminder']._cron_auto_reminder(test_mode=False)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Relances envoyees',
                'message': f"Creees: {result.get('created', 0)}, Envoyees: {result.get('sent', 0)}",
                'type': 'success',
                'sticky': True,
            }
        }

    def action_test_auto_reminder_dry_run(self):
        """Simule les relances automatiques SANS envoyer d'emails (mode test)"""
        result = self.env['lolirine.invoice.reminder']._cron_auto_reminder(test_mode=True)
        
        details = result.get('details', [])
        
        if not details:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Simulation terminee',
                    'message': 'Aucune relance a envoyer pour le moment.',
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        # Creer le wizard avec les lignes
        wizard = self.env['lolirine.invoice.reminder.simulation.wizard'].create({})
        
        # Creer les lignes
        for d in details:
            self.env['lolirine.invoice.reminder.simulation.line'].create({
                'wizard_id': wizard.id,
                'invoice_id': d.get('invoice_id'),
                'partner_id': d.get('partner_id'),
                'invoice_name': d.get('invoice'),
                'partner_name': d.get('partner'),
                'partner_email': d.get('email'),
                'amount_due': d.get('amount_due', 0),
                'days_overdue': d.get('days_overdue', 0),
                'reminder_type': d.get('reminder_type'),
                'fee': d.get('fee', 0),
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Simulation des relances',
            'res_model': 'lolirine.invoice.reminder.simulation.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
