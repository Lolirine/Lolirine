from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_sent = fields.Boolean(string="Envoye Peppol", default=False, copy=False)
    peppol_sent_date = fields.Datetime(string="Date envoi Peppol", copy=False)
    auto_send_invoice = fields.Boolean(
        string="Envoi auto email",
        related='partner_id.auto_send_invoice',
        readonly=True
    )
    auto_send_peppol = fields.Boolean(
        string="Envoi auto Peppol",
        related='partner_id.auto_send_peppol',
        readonly=True
    )

    def action_preview_invoice(self):
        """Aperçu PDF de la facture"""
        self.ensure_one()
        return self.env.ref('account.account_invoices').report_action(self)

    def action_preview_invoice_html(self):
        """Ouvrir l'aperçu dans le portail"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_portal_url(),
            'target': 'new',
        }

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

    def action_send_peppol(self):
        """Envoyer via Peppol (placeholder)"""
        self.ensure_one()
        # TODO: Implémenter l'envoi Peppol réel
        self.write({
            'peppol_sent': True,
            'peppol_sent_date': fields.Datetime.now(),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Peppol',
                'message': 'Facture marquée comme envoyée via Peppol',
                'type': 'success',
            }
        }
