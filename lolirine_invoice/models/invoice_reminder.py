# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class InvoiceReminder(models.Model):
    """Suivi des relances pour factures impayees"""
    _name = 'lolirine.invoice.reminder'
    _description = 'Relance facture'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=True,
        ondelete='cascade',
        domain=[('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted')]
    )
    
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string='Client',
        store=True
    )
    
    reminder_type = fields.Selection([
        ('reminder_1', '1er Rappel'),
        ('reminder_2', '2eme Rappel'),
        ('reminder_3', '3eme Rappel'),
        ('formal_notice', 'Mise en demeure'),
        ('lawyer', 'Transmission avocat'),
    ], string='Type de relance', required=True, default='reminder_1', tracking=True)
    
    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    
    send_date = fields.Datetime(
        string='Date envoi',
        readonly=True
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyee'),
        ('paid', 'Payee'),
        ('cancelled', 'Annulee'),
    ], string='Etat', default='draft', tracking=True)
    
    amount_due = fields.Monetary(
        related='invoice_id.amount_residual',
        string='Montant du'
    )
    
    currency_id = fields.Many2one(
        related='invoice_id.currency_id'
    )
    
    days_overdue = fields.Integer(
        string='Jours de retard',
        compute='_compute_days_overdue'
    )
    
    penalty_amount = fields.Monetary(
        string='Penalites de retard',
        compute='_compute_penalty_amount',
        help='Penalites calculees selon le taux legal belge'
    )
    
    notes = fields.Text(string='Notes internes')
    
    email_sent = fields.Boolean(string='Email envoye', default=False)
    
    company_id = fields.Many2one(
        related='invoice_id.company_id',
        store=True
    )

    @api.depends('invoice_id', 'reminder_type', 'date')
    def _compute_name(self):
        type_names = {
            'reminder_1': 'R1',
            'reminder_2': 'R2',
            'reminder_3': 'R3',
            'formal_notice': 'MED',
            'lawyer': 'AVO',
        }
        for rec in self:
            if rec.invoice_id and rec.reminder_type:
                rec.name = f"{type_names.get(rec.reminder_type, 'REL')}/{rec.invoice_id.name}"
            else:
                rec.name = 'Nouvelle relance'

    @api.depends('invoice_id.invoice_date_due')
    def _compute_days_overdue(self):
        today = fields.Date.today()
        for rec in self:
            if rec.invoice_id.invoice_date_due:
                delta = today - rec.invoice_id.invoice_date_due
                rec.days_overdue = max(0, delta.days)
            else:
                rec.days_overdue = 0

    @api.depends('invoice_id.amount_residual', 'days_overdue')
    def _compute_penalty_amount(self):
        """Calcul des penalites selon le taux legal belge (10.5% annuel pour 2024)"""
        annual_rate = 0.105  # Taux legal belge 2024
        for rec in self:
            if rec.days_overdue > 0 and rec.invoice_id.amount_residual > 0:
                # Penalites = Montant * (Taux / 365) * Jours de retard
                rec.penalty_amount = rec.invoice_id.amount_residual * (annual_rate / 365) * rec.days_overdue
            else:
                rec.penalty_amount = 0.0

    def action_send_reminder(self):
        """Envoyer la relance par email"""
        self.ensure_one()
        
        if not self.partner_id.email:
            raise UserError(_("Le client n'a pas d'adresse email configuree."))
        
        # Selectionner le template selon le type
        template_map = {
            'reminder_1': 'lolirine_invoice.email_template_reminder_1',
            'reminder_2': 'lolirine_invoice.email_template_reminder_2',
            'reminder_3': 'lolirine_invoice.email_template_reminder_3',
            'formal_notice': 'lolirine_invoice.email_template_formal_notice',
        }
        
        template_ref = template_map.get(self.reminder_type)
        if template_ref:
            template = self.env.ref(template_ref, raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)
        
        self.write({
            'state': 'sent',
            'send_date': fields.Datetime.now(),
            'email_sent': True,
        })
        
        # Mettre a jour le compteur de relances sur la facture
        self.invoice_id._compute_reminder_count()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Relance envoyee'),
                'message': _('Email envoye a %s') % self.partner_id.email,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_mark_paid(self):
        """Marquer comme payee"""
        self.write({'state': 'paid'})

    def action_cancel(self):
        """Annuler la relance"""
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.write({'state': 'draft'})

    # ==================== AUTO-RELANCE CRON ====================

    @api.model
    def _cron_auto_reminder(self):
        """Cron pour generer et envoyer automatiquement les relances"""
        import logging
        _logger = logging.getLogger(__name__)
        
        config = self.env['lolirine.invoice.reminder.config'].search(
            [('auto_reminder', '=', True)], limit=1
        )
        
        if not config:
            _logger.info("Auto-relance desactivee - pas de configuration active")
            return {'created': 0, 'sent': 0}
        
        _logger.info("=== Debut du traitement auto-relance ===")
        
        today = fields.Date.today()
        
        # Recuperer toutes les factures clients impayees en retard
        overdue_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('partner_id.email', '!=', False),
        ])
        
        _logger.info(f"Factures impayees trouvees: {len(overdue_invoices)}")
        
        reminders_created = 0
        reminders_sent = 0
        
        for invoice in overdue_invoices:
            days_overdue = (today - invoice.invoice_date_due).days
            
            # Determiner le type de relance appropriate
            reminder_type = self._get_reminder_type_for_days(days_overdue, config)
            
            if not reminder_type:
                continue
            
            # Verifier si une relance de ce type existe deja
            existing = self.search([
                ('invoice_id', '=', invoice.id),
                ('reminder_type', '=', reminder_type),
                ('state', '!=', 'cancelled'),
            ], limit=1)
            
            if existing:
                continue
            
            # Creer la relance
            try:
                reminder = self.create({
                    'invoice_id': invoice.id,
                    'reminder_type': reminder_type,
                    'date': today,
                    'notes': f'Relance automatique - {days_overdue} jours de retard',
                })
                reminders_created += 1
                _logger.info(f"Relance creee: {reminder.name} pour {invoice.partner_id.name}")
                
                # Envoyer automatiquement
                try:
                    reminder.action_send_reminder()
                    reminders_sent += 1
                    _logger.info(f"Relance envoyee: {reminder.name}")
                except Exception as e:
                    _logger.warning(f"Erreur envoi relance {reminder.name}: {e}")
                    
            except Exception as e:
                _logger.error(f"Erreur creation relance pour {invoice.name}: {e}")
        
        _logger.info(f"=== Fin auto-relance: {reminders_created} creees, {reminders_sent} envoyees ===")
        return {'created': reminders_created, 'sent': reminders_sent}

    @api.model
    def _get_reminder_type_for_days(self, days_overdue, config):
        """Determine le type de relance selon le nombre de jours de retard"""
        if days_overdue >= config.formal_notice_days:
            return 'formal_notice'
        elif days_overdue >= config.reminder_3_days:
            return 'reminder_3'
        elif days_overdue >= config.reminder_2_days:
            return 'reminder_2'
        elif days_overdue >= config.reminder_1_days:
            return 'reminder_1'
        return False

    @api.model
    def _cron_check_paid(self):
        """Cron pour marquer les relances comme payees si la facture est reglee"""
        open_reminders = self.search([
            ('state', 'in', ('draft', 'sent')),
        ])
        
        for reminder in open_reminders:
            if reminder.invoice_id.payment_state in ('paid', 'reversed'):
                reminder.write({'state': 'paid'})


class InvoiceReminderConfig(models.Model):
    """Configuration des delais de relance"""
    _name = 'lolirine.invoice.reminder.config'
    _description = 'Configuration relances'

    name = fields.Char(string='Nom', default='Configuration par defaut')
    
    reminder_1_days = fields.Integer(
        string='1er rappel apres',
        default=7,
        help='Nombre de jours apres echeance pour le 1er rappel'
    )
    reminder_2_days = fields.Integer(
        string='2eme rappel apres',
        default=14,
        help='Nombre de jours apres echeance pour le 2eme rappel'
    )
    reminder_3_days = fields.Integer(
        string='3eme rappel apres',
        default=21,
        help='Nombre de jours apres echeance pour le 3eme rappel'
    )
    formal_notice_days = fields.Integer(
        string='Mise en demeure apres',
        default=30,
        help='Nombre de jours apres echeance pour la mise en demeure'
    )
    
    penalty_rate = fields.Float(
        string='Taux de penalite annuel (%)',
        default=10.5,
        help='Taux legal belge pour les penalites de retard'
    )
    
    fee_reminder_3 = fields.Float(
        string='Frais 3eme rappel (EUR)',
        default=20.0,
        help='Frais factures automatiquement au 3eme rappel'
    )
    
    fee_formal_notice = fields.Float(
        string='Frais mise en demeure (EUR)',
        default=50.0,
        help='Frais factures automatiquement a la mise en demeure'
    )
    
    auto_reminder = fields.Boolean(
        string='Relances automatiques',
        default=False,
        help='Generer automatiquement les relances selon le calendrier'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company
    )
    
    def action_test_auto_reminder(self):
        """Lancer manuellement le processus d'auto-relance pour test"""
        result = self.env['lolirine.invoice.reminder']._cron_auto_reminder()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test auto-relance termine',
                'message': f"Creees: {result.get('created', 0)}, Envoyees: {result.get('sent', 0)}",
                'type': 'success' if result.get('created', 0) > 0 else 'warning',
                'sticky': True,
            }
        }
