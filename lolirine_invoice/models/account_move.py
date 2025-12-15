from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_preview_invoice(self):
        """Ouvrir un apercu de la facture dans une nouvelle fenetre"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        # Ouvrir le rapport PDF dans une nouvelle fenetre du navigateur
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/account.report_invoice/%s' % self.id,
            'target': 'new',
        }

    def action_preview_invoice_html(self):
        """Ouvrir un apercu HTML de la facture (plus rapide)"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/account.report_invoice/%s' % self.id,
            'target': 'new',
        }

    def action_confirm_and_send(self):
        """Confirmer la facture et ouvrir le wizard d'envoi"""
        self.ensure_one()
        
        # Si la facture est en brouillon, la confirmer d'abord
        if self.state == 'draft':
            self.action_post()
        
        # Ouvrir le wizard d'envoi
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
        """Envoyer la facture par email directement avec le template"""
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
