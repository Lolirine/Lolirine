# -*- coding: utf-8 -*-

from odoo import models, api


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail_now(self):
        """
        Envoie l'email immédiatement sans passer par la file d'attente.
        Utilise force_send=True pour un envoi instantané.
        """
        # Sauvegarder le contexte original
        self = self.with_context(mail_notify_force_send=True)
        
        # Appeler la méthode standard d'envoi avec force_send
        for wizard in self:
            # Envoyer via le template si disponible
            if wizard.template_id:
                # Utiliser send_mail du template avec force_send
                for res_id in wizard.res_ids or [wizard.res_id]:
                    wizard.template_id.send_mail(
                        res_id,
                        force_send=True,
                        email_values={
                            'email_to': wizard.email_to,
                            'subject': wizard.subject,
                        } if wizard.email_to else None
                    )
            else:
                # Envoi standard avec force_send via le contexte
                wizard.with_context(mail_notify_force_send=True)._action_send_mail(force_send=True)
        
        # Notification de succès
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
