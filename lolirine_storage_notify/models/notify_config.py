from odoo import models, fields, api


class LolirineNotifyConfig(models.Model):
    """
    Modèle singleton pour la configuration des notifications.
    Remplace res.config.settings pour éviter tout conflit
    avec la page Paramètres généraux d'Odoo.
    """
    _name = 'lolirine.notify.config'
    _description = 'Configuration Notifications Lolirine'

    # Garantir un seul enregistrement (singleton)
    _rec_name = 'id'

    # ── Événements ──────────────────────────────────────
    notify_signup = fields.Boolean(
        string='Inscriptions portail',
        default=True,
    )
    notify_rdv = fields.Boolean(
        string='Demandes de rendez-vous',
        default=True,
    )
    notify_contact = fields.Boolean(
        string='Formulaires de contact web',
        default=True,
    )
    notify_portal_msg = fields.Boolean(
        string='Messages portail client',
        default=True,
    )

    # ── VAPID ────────────────────────────────────────────
    vapid_email = fields.Char(
        string='Email de contact VAPID',
        default='admin@lolirine.be',
    )
    vapid_public_key = fields.Char(
        string='Clé publique VAPID',
    )
    vapid_private_key = fields.Char(
        string='Clé privée VAPID',
    )

    @api.model
    def get_config(self):
        """Retourne (et crée si besoin) l'enregistrement singleton."""
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config

    def action_open_vapid_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assistant clés VAPID',
            'res_model': 'lolirine.vapid.setup.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'lolirine_storage_notify.view_vapid_setup_wizard_form'
            ).id,
            'target': 'new',
            'context': {'default_vapid_email': self.vapid_email},
        }

    def action_test_notification(self):
        self.env['lolirine.notify.mixin']._lolirine_notify(
            event_type='default',
            title='Test Lolirine Notify',
            message='Les 3 canaux de notification fonctionnent correctement !',
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
