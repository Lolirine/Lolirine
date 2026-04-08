# -*- coding: utf-8 -*-
"""
Middleware CORS pour Odoo 19.
Injecte les en-têtes Access-Control-* sur toutes les réponses JSON-RPC
et gère les requêtes preflight OPTIONS.

Origines autorisées configurables via :
  Paramètres système > lolirine.cors.allowed_origins
  (valeur par défaut : https://claude.ai)
"""

import logging
from werkzeug.wrappers import Response
from odoo.http import request
from odoo import http
from odoo.tools import config

_logger = logging.getLogger(__name__)

# Origines toujours autorisées (en plus de celles en base)
ALWAYS_ALLOWED = {
    'https://claude.ai',
    'https://www.lolirinepoolstore.be',
    'http://localhost:8069',
    'http://127.0.0.1:8069',
}


def _get_allowed_origins():
    """Récupère la liste des origines depuis ir.config_parameter."""
    try:
        param = http.request.env['ir.config_parameter'].sudo().get_param(
            'lolirine.cors.allowed_origins', ''
        )
        extras = {o.strip() for o in param.split(',') if o.strip()}
        return ALWAYS_ALLOWED | extras
    except Exception:
        return ALWAYS_ALLOWED


class CORSMiddleware:
    """Wrapper WSGI qui ajoute les en-têtes CORS à chaque réponse."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        origin = environ.get('HTTP_ORIGIN', '')
        method = environ.get('REQUEST_METHOD', '')
        path   = environ.get('PATH_INFO', '')

        # On traite uniquement les routes JSON-RPC / API web
        is_api = (
            path.startswith('/web/dataset/')
            or path.startswith('/web/action/')
            or path.startswith('/api/')
        )

        if not is_api:
            return self.app(environ, start_response)

        # Récupération dynamique des origines autorisées
        try:
            allowed = _get_allowed_origins()
        except Exception:
            allowed = ALWAYS_ALLOWED

        origin_allowed = origin in allowed

        # Preflight OPTIONS — répondre directement sans passer par Odoo
        if method == 'OPTIONS' and origin_allowed:
            response = Response(status=204)
            response.headers.update(self._cors_headers(origin))
            return response(environ, start_response)

        # Requête normale — laisser Odoo traiter, puis injecter les headers
        def cors_start_response(status, headers, exc_info=None):
            if origin_allowed:
                # Filtrer les doublons éventuels
                headers = [
                    (k, v) for k, v in headers
                    if k.lower() not in (
                        'access-control-allow-origin',
                        'access-control-allow-credentials',
                        'access-control-allow-methods',
                        'access-control-allow-headers',
                        'access-control-expose-headers',
                        'vary',
                    )
                ]
                headers += list(self._cors_headers(origin).items())
            return start_response(status, headers, exc_info)

        return self.app(environ, cors_start_response)

    @staticmethod
    def _cors_headers(origin):
        return {
            'Access-Control-Allow-Origin':      origin,
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Methods':     'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers':     (
                'Content-Type, Authorization, X-Requested-With, '
                'X-Odoo-Session-Id, Accept'
            ),
            'Access-Control-Expose-Headers':    'X-Odoo-Session-Id',
            'Vary': 'Origin',
        }


# ── Patch au démarrage du serveur ──────────────────────────────────────────
# On monkey-patche l'application WSGI Odoo pour y insérer notre middleware.
# Cette approche est compatible Odoo 17/18/19 et Odoo.sh.

def _patch_wsgi_app():
    """Enveloppe l'application WSGI principale d'Odoo avec CORSMiddleware."""
    try:
        import odoo.service.wsgi_server as wsgi_server
        original = wsgi_server.application

        if not isinstance(original, CORSMiddleware):
            wsgi_server.application = CORSMiddleware(original)
            _logger.info('[lolirine_cors] CORSMiddleware activé sur wsgi_server.application')

    except Exception as e:
        _logger.warning('[lolirine_cors] Impossible de patcher wsgi_server: %s', e)

    # Patch alternatif via odoo.http.root (Odoo 16+)
    try:
        import odoo.http as odoo_http
        if hasattr(odoo_http, 'root') and odoo_http.root is not None:
            if not isinstance(odoo_http.root, CORSMiddleware):
                odoo_http.root = CORSMiddleware(odoo_http.root)
                _logger.info('[lolirine_cors] CORSMiddleware activé sur odoo.http.root')
    except Exception as e:
        _logger.warning('[lolirine_cors] Impossible de patcher odoo.http.root: %s', e)


_patch_wsgi_app()
