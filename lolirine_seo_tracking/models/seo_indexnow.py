# -*- coding: utf-8 -*-
"""IndexNow : signale instantanément les URL nouvelles/modifiées à Bing, Yandex,
Seznam, Naver... (Bing alimente aussi DuckDuckGo, Ecosia, Qwant en partie et la
recherche de ChatGPT). Google n'utilise pas IndexNow : il passe par le sitemap.
"""
import logging
from datetime import timedelta

import requests

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)

# Clé publique (par définition visible de tous), servie à la racine du site.
INDEXNOW_KEY = 'lolirinepoolstore7f3c9a2e5b41d8'
ENDPOINT = 'https://api.indexnow.org/indexnow'


class LolirineSeoIndexNow(models.AbstractModel):
    _name = 'lolirine.seo.indexnow'
    _description = 'Soumission IndexNow'

    @api.model
    def _key(self):
        return INDEXNOW_KEY

    @api.model
    def _changed_urls(self, website, since):
        lang_prefixes = [''] + [
            '/' + l.url_code for l in website.language_ids
            if l != website.default_lang_id]
        paths = set()
        products = self.env['product.template'].sudo().with_context(
            website_id=website.id, lang=website.default_lang_id.code).search([
                ('website_id', '=', website.id), ('is_published', '=', True),
                ('write_date', '>=', since)])
        for p in products:
            paths.add(p.website_url)
        # Les variantes NL/EN sont découvertes par les balises hreflang.
        pages = self.env['website.page'].sudo().search([
            ('website_id', '=', website.id), ('is_published', '=', True),
            ('write_date', '>=', since)])
        for pg in pages:
            for prefix in lang_prefixes:
                paths.add(prefix + pg.url)
        base = (website.domain or '').rstrip('/')
        if not base.startswith('http'):
            base = 'https://' + base
        return base, sorted(base + p for p in paths if p and p.startswith('/'))

    @api.model
    def _submit_recent(self, hours=26, force=False):
        cfg = self.env['lolirine.seo.config']
        if not force and cfg._get('indexnow_enabled') != '1':
            return 0
        since = fields.Datetime.now() - timedelta(hours=hours)
        total = 0
        for website in cfg._target_websites():
            if not website.domain:
                continue
            base, urls = self._changed_urls(website, since)
            host = base.split('://', 1)[-1]
            for chunk in tools.split_every(10000, urls):
                chunk = list(chunk)
                try:
                    resp = requests.post(ENDPOINT, json={
                        'host': host, 'key': INDEXNOW_KEY,
                        'keyLocation': '%s/%s.txt' % (base, INDEXNOW_KEY),
                        'urlList': chunk,
                    }, timeout=60)
                    _logger.info("lolirine_seo: IndexNow %s URL -> HTTP %s", len(chunk), resp.status_code)
                    if resp.status_code in (200, 202):
                        total += len(chunk)
                    else:
                        _logger.warning("lolirine_seo: IndexNow refusé : %s", resp.text[:300])
                except requests.RequestException as e:
                    _logger.warning("lolirine_seo: IndexNow injoignable : %s", e)
        cfg._set('indexnow_last', '%s (%s URL)' % (
            fields.Datetime.now().strftime('%d/%m/%Y %H:%M'), total))
        return total
