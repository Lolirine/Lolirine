from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lolirine_notify_vapid_public = fields.Char(
        string='Clé VAPID publique',
        config_parameter='lolirine_notify.vapid_public_key',
    )
    lolirine_notify_vapid_private = fields.Char(
        string='Clé VAPID privée',
        config_parameter='lolirine_notify.vapid_private_key',
    )
    lolirine_notify_vapid_email = fields.Char(
        string='Email VAPID (contact)',
        config_parameter='lolirine_notify.vapid_email',
        default='admin@lolirine.be',
    )
    lolirine_notify_signup = fields.Boolean(
        string='Notifier les inscriptions portail',
        config_parameter='lolirine_notify.notify_signup',
        default=True,
    )
    lolirine_notify_rdv = fields.Boolean(
        string='Notifier les demandes de RDV',
        config_parameter='lolirine_notify.notify_rdv',
        default=True,
    )
    lolirine_notify_contact = fields.Boolean(
        string='Notifier les formulaires de contact',
        config_parameter='lolirine_notify.notify_contact',
        default=True,
    )
    lolirine_notify_portal_msg = fields.Boolean(
        string='Notifier les messages portail',
        config_parameter='lolirine_notify.notify_portal_msg',
        default=True,
    )

    def action_open_vapid_wizard(self):
        """Ouvre l'assistant de génération des clés VAPID."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assistant clés VAPID',
            'res_model': 'lolirine.vapid.setup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {},
        }

    def action_test_notification_config(self):
        """Envoie une notification de test sur les 3 canaux."""
        self.env['lolirine.notify.mixin']._lolirine_notify(
            event_type='default',
            title='Test Lolirine Notify',
            message='Les 3 canaux de notification fonctionnent correctement sur ce poste !',
            partner=self.env.user.partner_id,
            url='/odoo/settings',
            activity_summary='Test notification',
            activity_note='<p>Ceci est un test des notifications Lolirine.</p>',
            activity_deadline_days=0,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test envoyé',
                'message': 'Notification de test envoyée sur les 3 canaux.',
                'type': 'success',
                'sticky': False,
            },
        }
