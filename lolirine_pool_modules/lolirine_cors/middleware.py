# -*- coding: utf-8 -*-
"""
Middleware CORS pour Odoo 19.
Injecte les en-têtes Access-Control-* sur toutes les réponses JSON-RPC
et gère les requêtes preflight OPTIONS.

Origines autorisées configurables via :
  Paramètres système > lolirine.cors.allowed_origins
"""

import logging
from werkzeug.wrappers import Response
from odoo import http

_logger = logging.getLogger(__name__)

ALWAYS_ALLOWED = {
    'https://claude.ai',
    'https://www.lolirinepoolstore.be',
    'http://localhost:8069',
    'http://127.0.0.1:8069',
}


def _get_allowed_origins():
    try:
        param = http.request.env['ir.config_parameter'].sudo().get_param(
            'lolirine.cors.allowed_origins', ''
        )
        extras = {o.strip() for o in param.split(',') if o.strip()}
        return ALWAYS_ALLOWED | extras
    except Exception:
        return ALWAYS_ALLOWED


class CORSMiddleware:
    """
    Wrapper WSGI transparent.

    Proxifie TOUS les attributs/méthodes vers l'objet sous-jacent afin
    qu'Odoo puisse appeler set_csp(), dispatch(), handle_error(), etc.
    sans provoquer d'AttributeError.
    """

    def __init__(self, app):
        # Bypass __setattr__ pour stocker sans recursion
        object.__setattr__(self, '_wrapped', app)

    # ── Proxy transparent ─────────────────────────────────────────────────
    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, '_wrapped'), name)

    def __setattr__(self, name, value):
        if name == '_wrapped':
            object.__setattr__(self, name, value)
        else:
            setattr(object.__getattribute__(self, '_wrapped'), name, value)

    def __delattr__(self, name):
        delattr(object.__getattribute__(self, '_wrapped'), name)

    def __repr__(self):
        return f'CORSMiddleware({object.__getattribute__(self, "_wrapped")!r})'

    # ── Interface WSGI ────────────────────────────────────────────────────
    def __call__(self, environ, start_response):
        app    = object.__getattribute__(self, '_wrapped')
        origin = environ.get('HTTP_ORIGIN', '')
        method = environ.get('REQUEST_METHOD', '')
        path   = environ.get('PATH_INFO', '')

        # Uniquement les routes JSON-RPC / API
        is_api = (
            path.startswith('/web/dataset/')
            or path.startswith('/web/action/')
            or path.startswith('/pool-checklist/')
            or path.startswith('/api/')
        )

        if not is_api or not origin:
            return app(environ, start_response)

        try:
            allowed = _get_allowed_origins()
        except Exception:
            allowed = ALWAYS_ALLOWED

        origin_allowed = origin in allowed

        # Preflight OPTIONS
        if method == 'OPTIONS' and origin_allowed:
            response = Response(status=204)
            response.headers.update(self._cors_headers(origin))
            return response(environ, start_response)

        # Requete normale : Odoo repond, puis on injecte les headers
        def cors_start_response(status, headers, exc_info=None):
            if origin_allowed:
                filtered = [
                    (k, v) for k, v in headers
                    if k.lower() not in {
                        'access-control-allow-origin',
                        'access-control-allow-credentials',
                        'access-control-allow-methods',
                        'access-control-allow-headers',
                        'access-control-expose-headers',
                        'vary',
                    }
                ]
                filtered += list(self._cors_headers(origin).items())
                return start_response(status, filtered, exc_info)
            return start_response(status, headers, exc_info)

        return app(environ, cors_start_response)

    @staticmethod
    def _cors_headers(origin):
        return {
            'Access-Control-Allow-Origin':      origin,
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Methods':     'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': (
                'Content-Type, Authorization, X-Requested-With, '
                'X-Odoo-Session-Id, Accept'
            ),
            'Access-Control-Expose-Headers': 'X-Odoo-Session-Id',
            'Vary': 'Origin',
        }


# ── Patch au demarrage ────────────────────────────────────────────────────
# On patche UNIQUEMENT wsgi_server.application (entree WSGI pure).
# On ne touche PAS odoo.http.root : c'est un objet Odoo riche (Root)
# dont les methodes (set_csp, dispatch...) sont appelees directement par
# le framework — remplacer root lui-meme casse les appels directs de type
# `root.set_csp(response)` effectues dans ir_http._post_dispatch.

def _patch_wsgi_app():
    try:
        import odoo.service.wsgi_server as wsgi_server
        if not isinstance(wsgi_server.application, CORSMiddleware):
            wsgi_server.application = CORSMiddleware(wsgi_server.application)
            _logger.info('[lolirine_cors] CORSMiddleware actif (wsgi_server.application)')
    except Exception as e:
        _logger.warning('[lolirine_cors] Patch wsgi_server echoue : %s', e)


_patch_wsgi_app()
