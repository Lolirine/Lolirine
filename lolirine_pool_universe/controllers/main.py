from odoo import http
from odoo.http import request

BLOCKS = ('showcase', 'tiles', 'lowprice')
SEASON_PREFIX = 'saison_'
HEADERS = [('Content-Type', 'text/html; charset=utf-8'), ('Cache-Control', 'no-store')]


class PoolUniverseController(http.Controller):

    def _empty(self):
        return request.make_response('', headers=HEADERS)

    def _campaign(self, code):
        website = request.website
        return request.env['lolirine.pool.campaign'].sudo().search([
            ('code', '=', code),
            ('website_id', 'in', [website.id, False]),
        ], limit=1)

    @http.route('/lolirine_universe/home_block/<string:block>', type='http', auth='public',
                website=True, sitemap=False, methods=['GET'])
    def home_block(self, block, **kwargs):
        """Fragment HTML d'un bloc déplaçable du constructeur (accueil ou encart saisonnier)."""
        website = request.website

        # Encarts saisonniers : affichés uniquement pendant leur période
        if block.startswith(SEASON_PREFIX):
            campaign = self._campaign(block[len(SEASON_PREFIX):])
            if not campaign or not campaign._in_period():
                return self._empty()
            data = campaign._block_data(website)
            if not data:
                return self._empty()
            html = request.env['ir.qweb']._render('lolirine_pool_universe.campaign_block', {
                'pc': data,
                'website': website,
            })
            return request.make_response(html, headers=HEADERS)

        # Blocs d'accueil
        if block not in BLOCKS or not website.pu_home_enabled:
            return self._empty()
        blocks = website._lolirine_home_blocks()
        if not blocks.get(block):
            return self._empty()
        html = request.env['ir.qweb']._render('lolirine_pool_universe.home_block_fragment', {
            'block': block,
            'pu_home': blocks,
            'website': website,
        })
        return request.make_response(html, headers=HEADERS)

    @http.route('/saison/<string:code>', type='http', auth='public', website=True, sitemap=False)
    def season_page(self, code, **kwargs):
        """Toute la sélection d'un encart saisonnier. Hors période : visible seulement en interne."""
        campaign = self._campaign(code)
        is_internal = request.env.user._is_internal()
        if not campaign or (not campaign._in_period() and not is_internal):
            raise request.not_found()
        return request.render('lolirine_pool_universe.campaign_page', {
            'pc': campaign._page_data(request.website),
        })
