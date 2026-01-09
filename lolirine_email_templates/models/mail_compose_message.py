# -*- coding: utf-8 -*-

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail_now(self):
        """
        Envoie l'email immédiatement sans passer par la file d'attente.
        Utilise force_send=True pour un envoi instantané.
        """
        for wizard in self:
            if wizard.template_id and wizard.res_ids:
                # Envoi via le template avec force_send
                for res_id in wizard.res_ids:
                    wizard.template_id.send_mail(res_id, force_send=True)
            elif wizard.template_id and wizard.res_id:
                # Envoi unique
                wizard.template_id.send_mail(wizard.res_id, force_send=True)
            else:
                # Envoi standard via le wizard
                wizard._action_send_mail(force_send=True)
        
        # Notification de succès et fermeture
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Envoi immédiat',
                'message': 'Email(s) envoyé(s) avec succès !',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
