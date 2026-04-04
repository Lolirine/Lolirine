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
