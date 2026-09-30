from odoo import http
from odoo.http import request

BLOCKS = ('showcase', 'tiles', 'lowprice')
HEADERS = [('Content-Type', 'text/html; charset=utf-8'), ('Cache-Control', 'no-store')]


class PoolUniverseController(http.Controller):

    @http.route('/lolirine_universe/home_block/<string:block>', type='http', auth='public',
                website=True, sitemap=False, methods=['GET'])
    def home_block(self, block, **kwargs):
        """Fragment HTML d'un bloc d'accueil, inséré par les blocs déplaçables du constructeur."""
        website = request.website
        if block not in BLOCKS or not website.pu_home_enabled:
            return request.make_response('', headers=HEADERS)
        blocks = website._lolirine_home_blocks()
        if not blocks.get(block):
            return request.make_response('', headers=HEADERS)
        html = request.env['ir.qweb']._render('lolirine_pool_universe.home_block_fragment', {
            'block': block,
            'pu_home': blocks,
            'website': website,
        })
        return request.make_response(html, headers=HEADERS)
