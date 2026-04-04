import json
import logging
from datetime import date, timedelta
from odoo import models, api, _

_logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
#  Icônes par type d'événement
# ─────────────────────────────────────────────────────────
ICONS = {
    'signup':  '🧑',
    'rdv':     '📅',
    'contact': '💬',
    'message': '📩',
    'default': '🔔',
}


class LolirineNotifyMixin(models.AbstractModel):
    _name = 'lolirine.notify.mixin'
    _description = 'Mixin de notification multi-canal Lolirine'

    # ─────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────

    def _get_notify_admin_partners(self):
        """Retourne les partner_id des admins via SQL (compatible toutes versions Odoo)."""
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        if not admin_group:
            return self.env['res.partner']
        self.env.cr.execute("""
            SELECT ru.partner_id FROM res_users ru
            JOIN res_groups_users_rel rel ON rel.uid = ru.id
            WHERE rel.gid = %s AND ru.active = true
        """, [admin_group.id])
        partner_ids = [r[0] for r in self.env.cr.fetchall()]
        return self.env['res.partner'].browse(partner_ids)

    def _get_notify_admins(self):
        """Retourne les res.users Administrateurs via SQL (compatible toutes versions Odoo)."""
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        if not admin_group:
            return self.env['res.users']
        self.env.cr.execute("""
            SELECT uid FROM res_groups_users_rel
            WHERE gid = %s
        """, [admin_group.id])
        user_ids = [r[0] for r in self.env.cr.fetchall()]
        return self.env['res.users'].browse(user_ids)

    # ─────────────────────────────────────────────────────
    #  Canal 1 – Bus.bus  (toast dans le backend)
    # ─────────────────────────────────────────────────────

    def _bus_notify(self, title, message, notif_type='info', url=None):
        """
        Envoie un toast via le bus Odoo à tous les administrateurs
        dont l'onglet backend est ouvert.
        """
        partners = self._get_notify_admin_partners()
        payload = {
            'title': title,
            'message': message,
            'type': notif_type,  # info | success | warning | danger
        }
        if url:
            payload['url'] = url
        for partner in partners:
            try:
                self.env['bus.bus']._sendone(partner, 'lolirine_notify', payload)
            except Exception as e:
                _logger.error("bus_notify error for partner %s: %s", partner.id, e)

    # ─────────────────────────────────────────────────────
    #  Canal 2 – mail.activity  (pastille orange native)
    # ─────────────────────────────────────────────────────

    def _activity_notify(self, partner, summary, note='', deadline_days=0,
                         activity_xmlid='lolirine_storage_notify.activity_type_portal_action'):
        """
        Crée une activité mail.activity sur le partenaire.
        Elle alimente le compteur orange dans le menu Odoo.
        """
        try:
            activity_type = self.env.ref(activity_xmlid, raise_if_not_found=False)
            if not activity_type:
                # Fallback sur Todo
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if not activity_type:
                _logger.warning("activity_notify: aucun type d'activité trouvé")
                return

            admins = self._get_notify_admins()
            responsible = admins[0] if admins else self.env.user

            deadline = date.today() + timedelta(days=deadline_days)

            partner.activity_schedule(
                activity_type_id=activity_type.id,
                summary=summary,
                note=note,
                user_id=responsible.id,
                date_deadline=deadline,
            )
        except Exception as e:
            _logger.error("activity_notify error for partner %s: %s", partner.id if partner else 'None', e)

    # ─────────────────────────────────────────────────────
    #  Canal 3 – Web Push  (OS level, navigateur fermé)
    # ─────────────────────────────────────────────────────

    def _web_push_notify(self, title, body, url='/web', icon=None):
        """
        Envoie une Web Push Notification à tous les abonnements actifs.
        Nécessite pywebpush et des clés VAPID configurées.
        """
        try:
            from pywebpush import webpush, WebPushException
        except ImportError:
            _logger.debug("pywebpush non installé – Web Push ignoré")
            return

        cfg = self.env['lolirine.notify.config'].sudo().get_config()
        vapid_private = cfg.vapid_private_key or ''
        vapid_public  = cfg.vapid_public_key or ''
        vapid_email   = cfg.vapid_email or 'admin@lolirine.be'

        if not vapid_private or not vapid_public:
            _logger.debug("Clés VAPID non configurées – Web Push ignoré")
            return

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'https://lolirine.be')
        if not icon:
            icon = base_url + '/web/static/img/favicon.ico'

        payload = json.dumps({
            'title': title,
            'body': body,
            'url': url,
            'icon': icon,
            'badge': base_url + '/lolirine_storage_notify/static/img/badge.png',
            'tag': 'lolirine-notify',
            'requireInteraction': False,
        })

        subscriptions = self.env['lolirine.push.subscription'].sudo().search([
            ('active', '=', True),
        ])

        deactivate_ids = []
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub.endpoint,
                        'keys': {
                            'p256dh': sub.p256dh,
                            'auth':   sub.auth,
                        }
                    },
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={'sub': f'mailto:{vapid_email}'},
                )
            except WebPushException as e:
                _logger.warning("Web Push failed [%s]: %s", sub.endpoint[:60], e)
                # 410 Gone / 404 = abonnement révoqué
                if hasattr(e, 'response') and e.response and e.response.status_code in (404, 410):
                    deactivate_ids.append(sub.id)
            except Exception as e:
                _logger.error("Web Push unexpected error: %s", e)

        if deactivate_ids:
            self.env['lolirine.push.subscription'].sudo().browse(deactivate_ids).write({'active': False})

    # ─────────────────────────────────────────────────────
    #  Point d'entrée unifié
    # ─────────────────────────────────────────────────────

    def _lolirine_notify(self, event_type, title, message,
                         partner=None, url='/web',
                         activity_summary=None, activity_note=None,
                         activity_deadline_days=1):
        """
        Déclenche les 3 canaux de notification simultanément.

        :param event_type: 'signup' | 'rdv' | 'contact' | 'message' | 'default'
        :param title:      Titre court de la notification
        :param message:    Corps du message
        :param partner:    res.partner concerné (pour l'activité)
        :param url:        URL de redirection sur clic
        :param activity_summary: Résumé de l'activité (si None = title)
        :param activity_note:    Note HTML de l'activité
        :param activity_deadline_days: Échéance en jours (défaut 1 = demain)
        """
        icon = ICONS.get(event_type, ICONS['default'])
        full_title = f"{icon} {title}"

        # 1 – Bus toast
        self._bus_notify(full_title, message, notif_type='info', url=url)

        # 2 – Activité sur le partenaire
        if partner:
            self._activity_notify(
                partner,
                summary=activity_summary or title,
                note=activity_note or f"<p>{message}</p>",
                deadline_days=activity_deadline_days,
            )

        # 3 – Web Push
        self._web_push_notify(full_title, message, url=url)
