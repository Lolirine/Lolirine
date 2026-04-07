from odoo import http
from odoo.http import request, Response


class WishlistController(http.Controller):

    @http.route('/shop/wishlist/config', type='json', auth='public',
                methods=['POST'], website=True, csrf=False)
    def wishlist_config(self, **kwargs):
        """Retourne la config (textes + couleurs) pour le JS."""
        cfg = request.env['lolirine.wishlist.config'].sudo()
        return {
            'texts': cfg.get_texts(),
            'css':   cfg.get_css_vars(),
        }

    @http.route('/shop/wishlist/css', type='http', auth='public',
                methods=['GET'], website=True, csrf=False)
    def wishlist_css(self, **kwargs):
        """Sert les variables CSS dynamiques."""
        css = request.env['lolirine.wishlist.config'].sudo().get_css_vars()
        return Response(css, content_type='text/css; charset=utf-8',
                        headers={'Cache-Control': 'no-cache'})
