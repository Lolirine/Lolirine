# -*- coding: utf-8 -*-

from odoo import models, fields, api


class InvoiceReminderSimulationWizard(models.TransientModel):
    _name = 'lolirine.invoice.reminder.simulation.wizard'
    _description = 'Simulation des relances automatiques'

    line_ids = fields.One2many('lolirine.invoice.reminder.simulation.line', 'wizard_id', string='Relances simulees')
    total_amount = fields.Float(string='Montant total du', compute='_compute_totals')
    total_fees = fields.Float(string='Total frais', compute='_compute_totals')
    count = fields.Integer(string='Nombre de relances', compute='_compute_totals')

    @api.depends('line_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount_due'))
            rec.total_fees = sum(rec.line_ids.mapped('fee'))
            rec.count = len(rec.line_ids)

    def action_execute_reminders(self):
        """Execute les relances pour de vrai"""
        self.env['lolirine.invoice.reminder']._cron_auto_reminder(test_mode=False)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Relances envoyees',
                'message': f'{self.count} relance(s) creee(s) et envoyee(s)',
                'type': 'success',
                'sticky': True,
            }
        }


class InvoiceReminderSimulationLine(models.TransientModel):
    _name = 'lolirine.invoice.reminder.simulation.line'
    _description = 'Ligne de simulation relance'

    wizard_id = fields.Many2one('lolirine.invoice.reminder.simulation.wizard', string='Wizard', ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Facture')
    partner_id = fields.Many2one('res.partner', string='Client')
    invoice_name = fields.Char(string='Facture')
    partner_name = fields.Char(string='Client')
    partner_email = fields.Char(string='Email')
    amount_due = fields.Float(string='Montant du')
    days_overdue = fields.Integer(string='Jours de retard')
    reminder_type = fields.Char(string='Type de relance')
    fee = fields.Float(string='Frais')

    def action_view_invoice(self):
        """Ouvre la facture"""
        self.ensure_one()
        if self.invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Facture',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.invoice_id.id,
            }

    def action_view_partner(self):
        """Ouvre le client"""
        self.ensure_one()
        if self.partner_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Client',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': self.partner_id.id,
            }
