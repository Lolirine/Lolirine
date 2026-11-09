# -*- coding: utf-8 -*-
"""Import Google Search Console (API searchAnalytics) via compte de service.

Authentification JWT RS256 signée avec `cryptography` (déjà requis par Odoo) :
aucune dépendance Python supplémentaire à installer sur Odoo.sh.
"""
import base64
import json
import logging
import time
from datetime import date, timedelta
from urllib.parse import quote

import requests

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TOKEN_URL = 'https://oauth2.googleapis.com/token'
API = 'https://www.googleapis.com/webmasters/v3'
SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly'


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=')


class LolirineSeoGscLine(models.Model):
    _name = 'lolirine.seo.gsc.line'
    _description = 'Search Console — requête × page × jour'
    _order = 'date desc, clicks desc, impressions desc'
    _rec_name = 'query'

    date = fields.Date('Jour', required=True, index=True)
    query = fields.Char('Requête', index=True)
    page = fields.Char('Page', index=True)
    country = fields.Char('Pays', size=3)
    device = fields.Selection([('DESKTOP', 'Ordinateur'), ('MOBILE', 'Mobile'),
                               ('TABLET', 'Tablette')], 'Appareil')
    clicks = fields.Integer('Clics', aggregator='sum')
    impressions = fields.Integer('Impressions', aggregator='sum')
    ctr = fields.Float('CTR (%)', digits=(6, 2), aggregator='avg')
    position = fields.Float('Position moyenne', digits=(6, 1), aggregator='avg')
    position_x_impr = fields.Float('Position × impressions', aggregator='sum',
                                   help="Sert au calcul de la position moyenne pondérée.")

    # ------------------------------------------------------------- auth/API
    @api.model
    def _gsc_token(self):
        cfg = self.env['lolirine.seo.config']
        raw = cfg._get('gsc_credentials')
        if not raw:
            raise UserError(_("Aucune clé de compte de service Google n'est configurée "
                              "(Site Web > SEO & Trafic > Réglages)."))
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        info = json.loads(raw)
        now = int(time.time())
        header = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
        claims = _b64(json.dumps({
            'iss': info['client_email'], 'scope': SCOPE, 'aud': TOKEN_URL,
            'iat': now, 'exp': now + 3600,
        }).encode())
        signing_input = header + b'.' + claims
        key = serialization.load_pem_private_key(info['private_key'].encode(), password=None)
        sig = _b64(key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256()))
        try:
            resp = requests.post(TOKEN_URL, data={
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': (signing_input + b'.' + sig).decode(),
            }, timeout=30)
        except requests.RequestException as e:
            raise UserError(_("Google injoignable : %s") % e)
        if resp.status_code != 200:
            raise UserError(_("Google a refusé l'authentification : %s") % resp.text[:500])
        return resp.json()['access_token']

    @api.model
    def _gsc_list_sites(self):
        token = self._gsc_token()
        resp = requests.get(API + '/sites', headers={'Authorization': 'Bearer ' + token}, timeout=30)
        if resp.status_code != 200:
            raise UserError(_("Search Console : %s") % resp.text[:500])
        return [s['siteUrl'] for s in resp.json().get('siteEntry', [])]

    @api.model
    def _gsc_query(self, token, site, start, end, start_row=0):
        url = '%s/sites/%s/searchAnalytics/query' % (API, quote(site, safe=''))
        body = {
            'startDate': start.isoformat(), 'endDate': end.isoformat(),
            'dimensions': ['date', 'query', 'page', 'country', 'device'],
            'rowLimit': 25000, 'startRow': start_row, 'dataState': 'all',
        }
        resp = requests.post(url, json=body, headers={'Authorization': 'Bearer ' + token},
                             timeout=120)
        if resp.status_code != 200:
            raise UserError(_("Search Console : %s") % resp.text[:500])
        return resp.json().get('rows', [])

    # ---------------------------------------------------------------- import
    @api.model
    def _gsc_import(self, days=None):
        cfg = self.env['lolirine.seo.config']
        site = cfg._get('gsc_site')
        if not site or not cfg._get('gsc_credentials'):
            _logger.info("lolirine_seo: Search Console non configurée, import ignoré")
            return 0
        token = self._gsc_token()
        end = date.today() - timedelta(days=1)
        last = self.search([], order='date desc', limit=1).date
        if days:
            start = end - timedelta(days=days - 1)
        elif last:
            # Les 4 derniers jours sont recalculés (données GSC encore provisoires)
            start = min(last, end) - timedelta(days=3)
        else:
            start = end - timedelta(days=int(cfg._get('gsc_backfill_days', 90) or 90) - 1)
        total = 0
        day = start
        while day <= end:
            chunk_end = min(day + timedelta(days=6), end)
            rows, offset = [], 0
            while True:
                batch = self._gsc_query(token, site, day, chunk_end, offset)
                rows += batch
                if len(batch) < 25000:
                    break
                offset += 25000
            self.search([('date', '>=', day), ('date', '<=', chunk_end)]).unlink()
            vals = []
            for r in rows:
                d, q, p, c, dev = r['keys']
                pos = float(r.get('position', 0))
                impr = int(r.get('impressions', 0))
                vals.append({
                    'date': d, 'query': q[:255], 'page': p[:500], 'country': (c or '')[:3].upper(),
                    'device': dev if dev in ('DESKTOP', 'MOBILE', 'TABLET') else False,
                    'clicks': int(r.get('clicks', 0)), 'impressions': impr,
                    'ctr': round(float(r.get('ctr', 0)) * 100, 2),
                    'position': round(pos, 1), 'position_x_impr': pos * impr,
                })
            for part in tools.split_every(2000, vals):
                self.create(list(part))
            total += len(vals)
            day = chunk_end + timedelta(days=1)
        cfg._set('gsc_last_import', '%s (%s lignes, %s → %s)' % (
            fields.Datetime.now().strftime('%d/%m/%Y %H:%M'), total, start, end))
        return total

    @api.model
    def _cron_import(self):
        try:
            self._gsc_import()
        except (UserError, requests.RequestException) as e:
            _logger.warning("lolirine_seo: import Search Console échoué : %s", e)


class LolirineSeoOpportunity(models.Model):
    """Synthèse 28 derniers jours par requête + page, avec type d'opportunité."""
    _name = 'lolirine.seo.opportunity'
    _description = 'Opportunités SEO (Search Console, 28 jours)'
    _auto = False
    _order = 'score desc'
    _rec_name = 'query'

    query = fields.Char('Requête', readonly=True)
    page = fields.Char('Page', readonly=True)
    clicks = fields.Integer('Clics', readonly=True)
    impressions = fields.Integer('Impressions', readonly=True)
    ctr = fields.Float('CTR (%)', digits=(6, 2), readonly=True, aggregator='avg')
    position = fields.Float('Position', digits=(6, 1), readonly=True, aggregator='avg')
    kind = fields.Selection([
        ('top3', 'Top 3 — à protéger'),
        ('low_ctr', 'Bien classé mais peu cliqué (titre/description à revoir)'),
        ('striking', 'Position 4–10 : pousser vers le top 3'),
        ('page2', 'Page 2 (11–20) : contenu / liens internes à renforcer'),
        ('far', 'Au-delà de 20'),
    ], 'Opportunité', readonly=True)
    score = fields.Float('Potentiel (clics supplémentaires estimés)', readonly=True, digits=(8, 1))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # CTR attendu approximatif par position (courbe moyenne observée e-commerce)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
              WITH agg AS (
                SELECT query, page,
                       SUM(clicks) AS clicks, SUM(impressions) AS impressions,
                       CASE WHEN SUM(impressions) > 0
                            THEN SUM(position_x_impr) / SUM(impressions) ELSE 0 END AS position
                  FROM lolirine_seo_gsc_line
                 WHERE date >= (CURRENT_DATE - 28) AND query IS NOT NULL
                 GROUP BY query, page
              ), x AS (
                SELECT *, CASE WHEN impressions > 0 THEN 100.0 * clicks / impressions ELSE 0 END AS ctr,
                       CASE WHEN position <= 1.5 THEN 28 WHEN position <= 2.5 THEN 15
                            WHEN position <= 3.5 THEN 10 WHEN position <= 5.5 THEN 6
                            WHEN position <= 10.5 THEN 3 WHEN position <= 20.5 THEN 1
                            ELSE 0.3 END AS exp_ctr
                  FROM agg
              )
              SELECT row_number() OVER () AS id, query, page, clicks, impressions,
                     ROUND(ctr::numeric, 2) AS ctr, ROUND(position::numeric, 1) AS position,
                     CASE WHEN position <= 3.5 AND ctr >= exp_ctr * 0.5 THEN 'top3'
                          WHEN position <= 7.5 AND ctr < exp_ctr * 0.5 THEN 'low_ctr'
                          WHEN position <= 10.5 THEN 'striking'
                          WHEN position <= 20.5 THEN 'page2'
                          ELSE 'far' END AS kind,
                     GREATEST(impressions * (CASE WHEN position <= 3.5 THEN exp_ctr
                                                  WHEN position <= 20.5 THEN 10 ELSE 3 END) / 100.0
                              - clicks, 0) AS score
                FROM x
            )
        """ % self._table)
