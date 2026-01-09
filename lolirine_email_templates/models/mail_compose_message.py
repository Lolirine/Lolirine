# -*- coding: utf-8 -*-

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail_now(self):
        """
        Envoie l'email immédiatement sans passer par la file d'attente.
        """
        # D'abord, envoyer via la méthode standard
        self.action_send_mail()
        
        # Ensuite, forcer l'envoi immédiat des emails en file d'attente
        outgoing_mails = self.env['mail.mail'].sudo().search([
            ('state', '=', 'outgoing')
        ], limit=50, order='create_date desc')
        
        if outgoing_mails:
            outgoing_mails.send()
        
        # Notification de succès
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Envoi immédiat',
                'message': 'Email(s) envoyé(s) avec succès !',
                'type': 'success',
                'sticky': False,
            }
        }
