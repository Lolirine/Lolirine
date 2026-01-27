# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InvoiceMassSendWizard(models.TransientModel):
    """Wizard pour envoyer plusieurs factures en masse"""
    _name = 'lolirine.invoice.mass.send.wizard'
    _description = 'Envoi groupe de factures'

    send_type = fields.Selection([
        ('email', 'Email uniquement'),
        ('peppol', 'Peppol uniquement'),
        ('both', 'Email et Peppol'),
    ], string='Type d\'envoi', default='email', required=True)
    
    invoice_ids = fields.Many2many(
        'account.move',
        string='Factures a envoyer',
        domain=[('state', '=', 'posted'), ('move_type', 'in', ('out_invoice', 'out_refund'))]
    )
    
    invoice_count = fields.Integer(
        string='Nombre de factures',
        compute='_compute_counts'
    )
    
    email_count = fields.Integer(
        string='Avec email',
        compute='_compute_counts'
    )
    
    peppol_count = fields.Integer(
        string='Avec Peppol',
        compute='_compute_counts'
    )
    
    skip_already_sent = fields.Boolean(
        string='Ignorer les deja envoyees',
        default=True
    )
    
    preview_line_ids = fields.One2many(
        'lolirine.invoice.mass.send.line',
        'wizard_id',
        string='Apercu'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            invoices = self.env['account.move'].browse(active_ids).filtered(
                lambda m: m.state == 'posted' and m.move_type in ('out_invoice', 'out_refund')
            )
            res['invoice_ids'] = [(6, 0, invoices.ids)]
        return res

    @api.depends('invoice_ids')
    def _compute_counts(self):
        for wizard in self:
            wizard.invoice_count = len(wizard.invoice_ids)
            wizard.email_count = len(wizard.invoice_ids.filtered(lambda i: i.partner_id.email))
            wizard.peppol_count = len(wizard.invoice_ids.filtered(
                lambda i: i.partner_id.peppol_eas and i.partner_id.peppol_endpoint
            ))

    @api.onchange('invoice_ids', 'send_type', 'skip_already_sent')
    def _onchange_generate_preview(self):
        """Generer l'apercu des envois"""
        lines = []
        for invoice in self.invoice_ids:
            can_email = bool(invoice.partner_id.email)
            can_peppol = bool(invoice.partner_id.peppol_eas and invoice.partner_id.peppol_endpoint)
            
            will_send_email = False
            will_send_peppol = False
            
            if self.send_type in ('email', 'both'):
                if can_email:
                    if not self.skip_already_sent or not invoice.is_move_sent:
                        will_send_email = True
            
            if self.send_type in ('peppol', 'both'):
                if can_peppol:
                    if not self.skip_already_sent or not invoice.peppol_sent:
                        will_send_peppol = True
            
            lines.append((0, 0, {
                'invoice_id': invoice.id,
                'partner_id': invoice.partner_id.id,
                'can_email': can_email,
                'can_peppol': can_peppol,
                'will_send_email': will_send_email,
                'will_send_peppol': will_send_peppol,
                'already_sent_email': invoice.is_move_sent,
                'already_sent_peppol': invoice.peppol_sent,
            }))
        
        self.preview_line_ids = [(5, 0, 0)] + lines

    def action_send(self):
        """Envoyer les factures"""
        self.ensure_one()
        
        sent_email = 0
        sent_peppol = 0
        errors = []
        
        for invoice in self.invoice_ids:
            # Envoi Email
            if self.send_type in ('email', 'both'):
                if invoice.partner_id.email:
                    if not self.skip_already_sent or not invoice.is_move_sent:
                        try:
                            if invoice._send_invoice_auto():
                                sent_email += 1
                        except Exception as e:
                            errors.append(f"{invoice.name}: {str(e)}")
            
            # Envoi Peppol
            if self.send_type in ('peppol', 'both'):
                if invoice.partner_id.peppol_eas and invoice.partner_id.peppol_endpoint:
                    if not self.skip_already_sent or not invoice.peppol_sent:
                        try:
                            if invoice._send_invoice_peppol_auto():
                                sent_peppol += 1
                        except Exception as e:
                            errors.append(f"{invoice.name} (Peppol): {str(e)}")
        
        # Message de resultat
        message_parts = []
        if sent_email > 0:
            message_parts.append(_('%d facture(s) envoyee(s) par email') % sent_email)
        if sent_peppol > 0:
            message_parts.append(_('%d facture(s) envoyee(s) via Peppol') % sent_peppol)
        if errors:
            message_parts.append(_('%d erreur(s)') % len(errors))
        
        message = ', '.join(message_parts) if message_parts else _('Aucun envoi effectue')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Envoi groupe termine'),
                'message': message,
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }


class InvoiceMassSendLine(models.TransientModel):
    """Ligne d'apercu pour l'envoi groupe"""
    _name = 'lolirine.invoice.mass.send.line'
    _description = 'Ligne apercu envoi groupe'

    wizard_id = fields.Many2one('lolirine.invoice.mass.send.wizard', ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Facture')
    partner_id = fields.Many2one('res.partner', string='Client')
    can_email = fields.Boolean(string='Email possible')
    can_peppol = fields.Boolean(string='Peppol possible')
    will_send_email = fields.Boolean(string='Envoi email')
    will_send_peppol = fields.Boolean(string='Envoi Peppol')
    already_sent_email = fields.Boolean(string='Deja envoye email')
    already_sent_peppol = fields.Boolean(string='Deja envoye Peppol')
