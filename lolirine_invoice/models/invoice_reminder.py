from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class InvoiceReminder(models.Model):
    _name = 'lolirine.invoice.reminder'
    _description = 'Relance facture'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', readonly=True, copy=False)
    invoice_id = fields.Many2one('account.move', string='Facture', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='invoice_id.partner_id', store=True, string='Client')
    company_id = fields.Many2one('res.company', related='invoice_id.company_id', store=True)
    
    reminder_type = fields.Selection([
        ('reminder_1', '1er Rappel'),
        ('reminder_2', '2eme Rappel'),
        ('reminder_3', '3eme Rappel'),
        ('formal_notice', 'Mise en demeure'),
    ], string='Type', required=True, default='reminder_1')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyee'),
        ('paid', 'Payee'),
        ('cancelled', 'Annulee'),
    ], string='Statut', default='draft', tracking=True)
    
    send_date = fields.Date(string='Date envoi')
    auto_generated = fields.Boolean(string='Generee auto', default=False)
    
    invoice_amount = fields.Monetary(related='invoice_id.amount_total', string='Montant facture')
    invoice_residual = fields.Monetary(related='invoice_id.amount_residual', string='Reste a payer')
    invoice_date_due = fields.Date(related='invoice_id.invoice_date_due', string='Echeance')
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    
    fee_invoice_id = fields.Many2one('account.move', string='Facture de frais', readonly=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                invoice = self.env['account.move'].browse(vals.get('invoice_id'))
                prefix = {'reminder_1': 'R1', 'reminder_2': 'R2', 'reminder_3': 'R3', 'formal_notice': 'MED'}.get(vals.get('reminder_type', 'reminder_1'), 'R')
                vals['name'] = f"{prefix}/{invoice.name}"
        return super().create(vals_list)

    def action_send(self):
        """Envoyer la relance par email"""
        self.ensure_one()
        if self._send_reminder_email():
            self.write({'state': 'sent', 'send_date': fields.Date.today()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_set_paid(self):
        self.write({'state': 'paid'})

    def _send_reminder_email(self):
        """Envoyer l'email de relance"""
        self.ensure_one()
        template_map = {
            'reminder_1': 'lolirine_invoice.email_template_reminder_1',
            'reminder_2': 'lolirine_invoice.email_template_reminder_2',
            'reminder_3': 'lolirine_invoice.email_template_reminder_3',
            'formal_notice': 'lolirine_invoice.email_template_formal_notice',
        }
        template_ref = template_map.get(self.reminder_type)
        template = self.env.ref(template_ref, raise_if_not_found=False)
        
        if not template:
            _logger.warning(f"Template {template_ref} non trouve")
            return False
        
        if not self.partner_id.email:
            _logger.warning(f"Pas d'email pour {self.partner_id.name}")
            return False
        
        try:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=f"Email de relance envoye a {self.partner_id.email}", message_type='notification')
            return True
        except Exception as e:
            _logger.error(f"Erreur envoi email relance {self.name}: {e}")
            return False

    def _add_fee_to_invoice(self, amount, description):
        """Creer une facture de frais"""
        self.ensure_one()
        
        product = self.env['product.product'].search([('default_code', '=', 'FRAIS_RAPPEL')], limit=1)
        if not product:
            product = self.env['product.product'].search([('name', 'ilike', 'frais')], limit=1)
        
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'quantity': 1,
                'price_unit': amount,
                'product_id': product.id if product else False,
            })],
            'ref': f"Frais - {self.invoice_id.name}",
        }
        
        fee_invoice = self.env['account.move'].create(invoice_vals)
        fee_invoice.action_post()
        self.fee_invoice_id = fee_invoice.id
        self.message_post(body=f"Facture de frais creee: {fee_invoice.name} ({amount}€)", message_type='notification')
        return fee_invoice

    def action_create_next_reminder(self):
        """Creer la relance suivante"""
        self.ensure_one()
        next_map = {'reminder_1': 'reminder_2', 'reminder_2': 'reminder_3', 'reminder_3': 'formal_notice'}
        next_type = next_map.get(self.reminder_type)
        
        if not next_type:
            raise UserError("Pas de niveau suivant apres la mise en demeure.")
        
        existing = self.search([
            ('invoice_id', '=', self.invoice_id.id),
            ('reminder_type', '=', next_type),
            ('state', '!=', 'cancelled'),
        ], limit=1)
        
        if existing:
            raise UserError(f"Une relance de ce type existe deja.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nouvelle relance',
            'res_model': 'lolirine.invoice.reminder',
            'view_mode': 'form',
            'context': {'default_invoice_id': self.invoice_id.id, 'default_reminder_type': next_type},
        }

    @api.model
    def _cron_auto_reminder(self, test_mode=False):
        """Cron pour generer et envoyer automatiquement les relances"""
        config = self.env['lolirine.invoice.reminder.config'].get_config()
        
        if not config.auto_reminder:
            _logger.info("Auto-relance desactivee")
            return {'created': 0, 'sent': 0}
        
        _logger.info("=== Debut auto-relance ===")
        today = fields.Date.today()
        
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('partner_id.email', '!=', False),
        ])
        
        _logger.info(f"Factures impayees: {len(invoices)}")
        
        created = sent = 0
        
        for inv in invoices:
            days = (today - inv.invoice_date_due).days
            
            # Determiner le type de relance
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
            
            # Verifier si deja existe
            if self.search([('invoice_id', '=', inv.id), ('reminder_type', '=', rtype), ('state', '!=', 'cancelled')], limit=1):
                continue
            
            # Verifier que le niveau precedent a ete envoye
            if rtype != 'reminder_1':
                prev = {'reminder_2': 'reminder_1', 'reminder_3': 'reminder_2', 'formal_notice': 'reminder_3'}.get(rtype)
                if not self.search([('invoice_id', '=', inv.id), ('reminder_type', '=', prev), ('state', '=', 'sent')], limit=1):
                    continue
            
            if test_mode:
                _logger.info(f"[TEST] Relance {rtype} pour {inv.name}")
                created += 1
                continue
            
            try:
                reminder = self.create({'invoice_id': inv.id, 'reminder_type': rtype, 'auto_generated': True})
                created += 1
                
                # Ajouter les frais pour 3eme rappel et mise en demeure
                if rtype == 'reminder_3' and config.fee_reminder_3 > 0:
                    reminder._add_fee_to_invoice(config.fee_reminder_3, f"Frais de rappel - {inv.name}")
                elif rtype == 'formal_notice' and config.fee_formal_notice > 0:
                    reminder._add_fee_to_invoice(config.fee_formal_notice, f"Frais de mise en demeure - {inv.name}")
                
                if reminder._send_reminder_email():
                    reminder.write({'state': 'sent', 'send_date': today})
                    sent += 1
            except Exception as e:
                _logger.error(f"Erreur auto-relance {inv.name}: {e}")
        
        _logger.info(f"Auto-relance: {created} creees, {sent} envoyees")
        return {'created': created, 'sent': sent, 'test_mode': test_mode}

    @api.model
    def _cron_check_paid(self):
        """Verifier les factures payees et mettre a jour les relances"""
        for r in self.search([('state', 'in', ['draft', 'sent']), ('invoice_id.payment_state', '=', 'paid')]):
            r.write({'state': 'paid'})
            r.message_post(body="Facture payee - cloture automatique", message_type='notification')


class InvoiceReminderConfig(models.Model):
    _name = 'lolirine.invoice.reminder.config'
    _description = 'Configuration relances'

    name = fields.Char(default='Configuration', required=True)
    reminder_1_days = fields.Integer(string='1er rappel (jours)', default=7)
    reminder_2_days = fields.Integer(string='2eme rappel (jours)', default=14)
    reminder_3_days = fields.Integer(string='3eme rappel (jours)', default=21)
    formal_notice_days = fields.Integer(string='Mise en demeure (jours)', default=30)
    fee_reminder_3 = fields.Float(string='Frais 3eme rappel (EUR)', default=20.0)
    fee_formal_notice = fields.Float(string='Frais mise en demeure (EUR)', default=50.0)
    auto_reminder = fields.Boolean(string='Auto-relance active', default=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def get_config(self):
        """Recuperer ou creer la configuration unique"""
        config = self.search([('company_id', '=', self.env.company.id)], limit=1)
        if not config:
            config = self.create({
                'name': 'Configuration',
                'company_id': self.env.company.id,
            })
        return config

    def action_open_config(self):
        """Action pour ouvrir la configuration existante"""
        config = self.get_config()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configuration des relances',
            'res_model': 'lolirine.invoice.reminder.config',
            'view_mode': 'form',
            'res_id': config.id,
            'target': 'current',
        }

    def action_test_auto_reminder(self):
        """Executer les relances automatiques"""
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

    def action_test_dry_run(self):
        """Simuler les relances (sans envoyer)"""
        result = self.env['lolirine.invoice.reminder']._cron_auto_reminder(test_mode=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Simulation terminee',
                'message': f"Relances qui seraient creees: {result.get('created', 0)}",
                'type': 'info',
                'sticky': True,
            }
        }
