from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_sent = fields.Boolean(string="Envoye Peppol", default=False, copy=False)
    peppol_sent_date = fields.Datetime(string="Date envoi Peppol", copy=False)

    def action_preview_invoice(self):
        """Apercu PDF de la facture"""
        self.ensure_one()
        return self.env.ref('account.account_invoices').report_action(self)

    def action_confirm_and_send(self):
        """Confirmer et envoyer la facture"""
        self.ensure_one()
        if self.state == 'draft':
            self.action_post()
        return self.action_open_send_wizard()

    def action_open_send_wizard(self):
        """Ouvrir l'assistant d'envoi"""
        self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Envoyer la facture',
            'res_model': 'account.move.send',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'default_mail_template_id': template.id if template else False,
            },
        }
