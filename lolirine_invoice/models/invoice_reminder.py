# -*- coding: utf-8 -*-

import base64
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
        domain=[('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted')],
        tracking=True
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
        string='Montant du',
        store=True
    )
    
    currency_id = fields.Many2one(
        related='invoice_id.currency_id'
    )
    
    days_overdue = fields.Integer(
        string='Jours de retard',
        compute='_compute_days_overdue',
        store=True
    )
    
    penalty_amount = fields.Monetary(
        string='Penalites de retard',
        compute='_compute_penalty_amount',
        store=True,
        help='Penalites calculees selon le taux legal belge'
    )
    
    total_due = fields.Monetary(
        string='Total du',
        compute='_compute_penalty_amount',
        store=True,
        help='Montant du + penalites'
    )
    
    notes = fields.Text(string='Notes internes')
    
    email_sent = fields.Boolean(string='Email envoye', default=False)
    
    company_id = fields.Many2one(
        related='invoice_id.company_id',
        store=True
    )

    # ==================== COMPUTE METHODS ====================

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
            if rec.invoice_id and rec.invoice_id.invoice_date_due:
                delta = today - rec.invoice_id.invoice_date_due
                rec.days_overdue = max(0, delta.days)
            else:
                rec.days_overdue = 0

    @api.depends('amount_due', 'days_overdue')
    def _compute_penalty_amount(self):
        """Calcul des penalites selon le taux legal belge (10.5% annuel pour 2024)"""
        annual_rate = 0.105  # Taux legal belge 2024
        for rec in self:
            if rec.days_overdue > 0 and rec.amount_due > 0:
                # Penalites = Montant * (Taux / 365) * Jours de retard
                rec.penalty_amount = rec.amount_due * (annual_rate / 365) * rec.days_overdue
                rec.total_due = rec.amount_due + rec.penalty_amount
            else:
                rec.penalty_amount = 0.0
                rec.total_due = rec.amount_due or 0.0

    # ==================== ACTIONS ====================

    def action_send_reminder(self):
        """Envoyer la relance par email avec la facture en piece jointe"""
        self.ensure_one()
        
        if not self.partner_id.email:
            raise UserError(_("Le client n'a pas d'adresse email configuree."))
        
        if not self.invoice_id:
            raise UserError(_("Aucune facture associee a cette relance."))
        
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
                # Generer le PDF de la facture
                report = self.env.ref('account.account_invoices')
                pdf_content, _ = report._render_qweb_pdf(report.id, [self.invoice_id.id])
                
                # Creer la piece jointe
                attachment = self.env['ir.attachment'].create({
                    'name': f"{self.invoice_id.name.replace('/', '_')}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'lolirine.invoice.reminder',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                
                # Envoyer l'email avec la piece jointe
                template.send_mail(
                    self.id, 
                    force_send=True,
                    email_values={'attachment_ids': [attachment.id]}
                )
            else:
                raise UserError(_("Le template d'email '%s' n'a pas ete trouve.") % template_ref)
        
        self.write({
            'state': 'sent',
            'send_date': fields.Datetime.now(),
            'email_sent': True,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Relance envoyee'),
                'message': _('Email envoye a %s avec la facture en piece jointe') % self.partner_id.email,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_composer(self):
        """Ouvrir le compositeur d'email pour previsualiser avant envoi"""
        self.ensure_one()
        
        template_map = {
            'reminder_1': 'lolirine_invoice.email_template_reminder_1',
            'reminder_2': 'lolirine_invoice.email_template_reminder_2',
            'reminder_3': 'lolirine_invoice.email_template_reminder_3',
            'formal_notice': 'lolirine_invoice.email_template_formal_notice',
        }
        
        template_ref = template_map.get(self.reminder_type)
        template = self.env.ref(template_ref, raise_if_not_found=False) if template_ref else False
        
        # Generer le PDF de la facture pour la previsualisation
        attachment_ids = []
        if self.invoice_id:
            report = self.env.ref('account.account_invoices')
            pdf_content, _ = report._render_qweb_pdf(report.id, [self.invoice_id.id])
            
            attachment = self.env['ir.attachment'].create({
                'name': f"{self.invoice_id.name.replace('/', '_')}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'lolirine.invoice.reminder',
                'res_id': self.id,
                'mimetype': 'application/pdf',
            })
            attachment_ids = [attachment.id]
        
        ctx = {
            'default_model': 'lolirine.invoice.reminder',
            'default_res_ids': self.ids,
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'default_attachment_ids': attachment_ids,
            'force_email': True,
        }
        
        return {
            'name': _('Envoyer la relance'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': ctx,
        }

    def action_mark_paid(self):
        """Marquer comme payee"""
        self.write({'state': 'paid'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Relance cloturee'),
                'message': _('La relance a ete marquee comme payee.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Annuler la relance"""
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.write({
            'state': 'draft',
            'send_date': False,
            'email_sent': False,
        })

    def action_view_invoice(self):
        """Voir la facture associee"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }

    def action_create_next_reminder(self):
        """Creer la relance suivante"""
        self.ensure_one()
        
        next_type_map = {
            'reminder_1': 'reminder_2',
            'reminder_2': 'reminder_3',
            'reminder_3': 'formal_notice',
            'formal_notice': 'lawyer',
        }
        
        next_type = next_type_map.get(self.reminder_type)
        if not next_type:
            raise UserError(_("Aucune relance suivante disponible apres ce niveau."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle relance'),
            'res_model': 'lolirine.invoice.reminder',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_invoice_id': self.invoice_id.id,
                'default_reminder_type': next_type,
            },
        }


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
