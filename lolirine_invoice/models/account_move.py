from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    auto_send_invoice = fields.Boolean(
        string="Envoi automatique",
        default=False,
        help="Si active, la facture sera envoyee automatiquement par email apres confirmation"
    )

    def action_post(self):
        """Override pour envoyer automatiquement la facture après confirmation"""
        res = super().action_post()
        
        # Envoyer automatiquement si l'option est activée
        for move in self:
            if move.auto_send_invoice and move.move_type in ('out_invoice', 'out_refund'):
                move._send_invoice_auto()
        
        return res

    def _send_invoice_auto(self):
        """Envoyer la facture automatiquement par email"""
        self.ensure_one()
        
        if not self.partner_id.email:
            # Log un message si pas d'email
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

    def action_preview_invoice(self):
        """Ouvrir un apercu de la facture dans une nouvelle fenetre"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        # Utiliser le rapport de facture avec QR code (template personnalisé Odoo)
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/account.report_invoice_with_payments/%s' % self.id,
            'target': 'new',
        }

    def action_preview_invoice_html(self):
        """Ouvrir un apercu HTML de la facture (plus rapide)"""
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Cette action est uniquement disponible pour les factures clients."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/account.report_invoice_with_payments/%s' % self.id,
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


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    auto_send_invoice = fields.Boolean(
        string="Envoi auto factures",
        default=False,
        help="Si active, les factures de ce client seront envoyees automatiquement par email apres confirmation"
    )


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        """Override pour propager l'option d'envoi auto du client vers la facture"""
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        
        for move in moves:
            if move.partner_id.auto_send_invoice:
                move.auto_send_invoice = True
        
        return moves
