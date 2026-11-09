# -*- coding: utf-8 -*-
import json
import logging
import time
from collections import defaultdict, deque

from odoo import http
from odoo.http import request

from ..models import seo_sources as S
from ..models.seo_indexnow import INDEXNOW_KEY

_logger = logging.getLogger(__name__)

# Anti-abus simple, par processus : 60 pages vues / minute / adresse IP.
_RATE = defaultdict(deque)
_RATE_MAX, _RATE_WINDOW = 60, 60


def _throttled(ip):
    now = time.time()
    q = _RATE[ip]
    while q and now - q[0] > _RATE_WINDOW:
        q.popleft()
    if len(q) >= _RATE_MAX:
        return True
    q.append(now)
    if len(_RATE) > 5000:
        _RATE.clear()
    return False


class LolirineSeoController(http.Controller):

    @http.route('/lolirine_seo/hit', type='http', auth='public', methods=['POST'],
                csrf=False, website=True, sitemap=False, save_session=False)
    def hit(self, **kw):
        try:
            self._process_hit()
        except Exception:
            _logger.debug("lolirine_seo: hit ignoré", exc_info=True)
        return request.make_response('', status=204)

    def _process_hit(self):
        httpreq = request.httprequest
        raw = httpreq.get_data(cache=True, as_text=True)
        if not raw and httpreq.form:
            # corps envoyé en form-urlencoded : le JSON devient la 1re clé du formulaire
            raw = next(iter(httpreq.form.keys()), '')
        if not raw or len(raw) > 4000:
            return
        ua = httpreq.headers.get('User-Agent', '')
        if S.is_bot(ua) or _throttled(httpreq.remote_addr or '?'):
            return
        website = request.website
        cfg = request.env['lolirine.seo.config'].sudo()
        if website.id not in cfg._target_website_ids():
            return
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return
        order = None
        if '/shop/confirmation' in (payload.get('p') or ''):
            order_id = request.session.get('sale_last_order_id')
            if order_id:
                order = request.env['sale.order'].sudo().browse(order_id).exists()
                if order and request.env['lolirine.seo.hit'].sudo().search_count(
                        [('order_id', '=', order.id)]):
                    return  # rechargement de la page de confirmation
        country = None
        geoip = getattr(request, 'geoip', None)
        if geoip:
            try:
                country = geoip.country_code
            except Exception:
                country = None
        request.env['lolirine.seo.hit']._record(website, payload, ua, country, order)

    @http.route('/%s.txt' % INDEXNOW_KEY, type='http', auth='public', sitemap=False)
    def indexnow_key(self):
        return request.make_response(INDEXNOW_KEY, headers=[('Content-Type', 'text/plain')])
