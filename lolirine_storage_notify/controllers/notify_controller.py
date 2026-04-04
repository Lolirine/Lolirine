import json
import logging
import os
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class LolirineNotifyController(http.Controller):

    # ─────────────────────────────────────────────────────
    #  Service Worker – doit être servi depuis la racine
    # ─────────────────────────────────────────────────────

    @http.route('/sw-lolirine.js', type='http', auth='public', methods=['GET'], csrf=False)
    def serve_service_worker(self, **kwargs):
        """Sert le Service Worker depuis la racine du domaine (obligatoire pour le scope)."""
        sw_path = os.path.join(
            os.path.dirname(__file__),
            '..', 'static', 'src', 'js', 'service_worker.js'
        )
        sw_path = os.path.normpath(sw_path)
        try:
            with open(sw_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            _logger.error("Service Worker file not found: %s", sw_path)
            content = "// Service Worker not found"

        return Response(
            content,
            content_type='application/javascript',
            headers={
                'Service-Worker-Allowed': '/',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
            }
        )

    # ─────────────────────────────────────────────────────
    #  VAPID public key endpoint
    # ─────────────────────────────────────────────────────

    @http.route('/lolirine/notify/vapid-public-key', type='http', auth='user', methods=['GET'], csrf=False)
    def get_vapid_public_key(self, **kwargs):
        """Retourne la clé VAPID publique pour l'abonnement push côté navigateur."""
        ICP = request.env['ir.config_parameter'].sudo()
        public_key = ICP.get_param('lolirine_notify.vapid_public_key', '')
        return Response(
            json.dumps({'publicKey': public_key}),
            content_type='application/json',
        )

    # ─────────────────────────────────────────────────────
    #  Enregistrement d'un abonnement push
    # ─────────────────────────────────────────────────────

    @http.route('/lolirine/notify/subscribe', type='json', auth='user', methods=['POST'], csrf=False)
    def subscribe_push(self, endpoint, p256dh, auth, user_agent=None, **kwargs):
        """Enregistre ou met à jour un abonnement Web Push."""
        try:
            sub_id = request.env['lolirine.push.subscription'].register(
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_agent=user_agent,
            )
            return {'success': True, 'id': sub_id}
        except Exception as e:
            _logger.error("subscribe_push error: %s", e)
            return {'success': False, 'error': str(e)}

    # ─────────────────────────────────────────────────────
    #  Désenregistrement d'un abonnement push
    # ─────────────────────────────────────────────────────

    @http.route('/lolirine/notify/unsubscribe', type='json', auth='user', methods=['POST'], csrf=False)
    def unsubscribe_push(self, endpoint, **kwargs):
        """Révoque un abonnement Web Push."""
        try:
            request.env['lolirine.push.subscription'].unregister(endpoint=endpoint)
            return {'success': True}
        except Exception as e:
            _logger.error("unsubscribe_push error: %s", e)
            return {'success': False, 'error': str(e)}

    # ─────────────────────────────────────────────────────
    #  Statut de l'abonnement courant
    # ─────────────────────────────────────────────────────

    @http.route('/lolirine/notify/status', type='json', auth='user', methods=['POST'], csrf=False)
    def push_status(self, endpoint=None, **kwargs):
        """Vérifie si l'endpoint est enregistré et actif."""
        if not endpoint:
            return {'subscribed': False}
        sub = request.env['lolirine.push.subscription'].sudo().search([
            ('endpoint', '=', endpoint),
            ('active', '=', True),
        ], limit=1)
        return {'subscribed': bool(sub), 'id': sub.id if sub else None}

    # ─────────────────────────────────────────────────────
    #  Test de notification (admin seulement)
    # ─────────────────────────────────────────────────────

    @http.route('/lolirine/notify/test', type='json', auth='user', methods=['POST'], csrf=False)
    def test_notification(self, **kwargs):
        """Envoie une notification de test sur tous les canaux."""
        if not request.env.user.has_group('base.group_system'):
            return {'success': False, 'error': 'Accès refusé'}
        try:
            mixin = request.env['lolirine.notify.mixin']
            mixin._lolirine_notify(
                event_type='default',
                title='Test de notification',
                message='Les notifications Lolirine fonctionnent correctement sur ce poste.',
                partner=request.env.user.partner_id,
                url='/odoo/settings',
                activity_summary='Test notification',
                activity_note='<p>Ceci est un test des notifications Lolirine.</p>',
                activity_deadline_days=0,
            )
            return {'success': True}
        except Exception as e:
            _logger.error("test_notification error: %s", e)
            return {'success': False, 'error': str(e)}
