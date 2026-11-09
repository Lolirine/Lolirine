# -*- coding: utf-8 -*-
import logging

from odoo import models
from odoo.http import request

from . import seo_sources as S

_logger = logging.getLogger(__name__)

# Fichiers que robots et scanners demandent en permanence : inutile de les suivre.
IGNORED_SUFFIXES = ('.php', '.asp', '.aspx', '.env', '.git', '.map', '.cgi', '.bak', '.sql')
IGNORED_PREFIXES = ('/wp-', '/wordpress', '/.well-known', '/xmlrpc', '/cgi-bin',
                    '/phpmyadmin', '/admin', '/vendor/', '/@vite', '/favicon')


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _handle_error(cls, exception):
        response = super()._handle_error(exception)
        try:
            if getattr(response, 'status_code', None) == 404:
                cls._lolirine_seo_log_404()
        except Exception:  # le suivi ne doit jamais casser la page 404
            _logger.debug("lolirine_seo: log 404 impossible", exc_info=True)
        return response

    @classmethod
    def _lolirine_seo_log_404(cls):
        website = getattr(request, 'website', None)
        if not website:
            return
        path = request.httprequest.path or '/'
        low = path.lower()
        if low.endswith(IGNORED_SUFFIXES) or low.startswith(IGNORED_PREFIXES) \
                or low.startswith(('/web/', '/lolirine_seo/')):
            return
        env = request.env
        icp_ids = env['lolirine.seo.config'].sudo()._target_website_ids()
        if website.id not in icp_ids:
            return
        ua = request.httprequest.headers.get('User-Agent', '')
        bot = S.bot_name(ua)
        referrer = request.httprequest.headers.get('Referer', '')
        # Curseur dédié : la transaction de la requête a été annulée (rollback)
        with env.registry.cursor() as cr:
            env['lolirine.seo.notfound']._log(cr, website.id, path, referrer, bot)
