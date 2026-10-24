import re
from odoo import http
from odoo.http import request

from ..models.livraison import langue, tr


class BuyPanelController(http.Controller):

    @http.route('/shop/buypanel/info', type='jsonrpc', auth='public', methods=['POST'], website=True, csrf=False)
    def buypanel_info(self, product_id=None, **kwargs):
        if not product_id:
            return {}

        product = request.env['product.product'].sudo().browse(int(product_id))
        if not product.exists():
            return {}

        tmpl = product.product_tmpl_id

        Liv = request.env['lolirine.livraison'].sudo()
        lg = langue(request.env)

        # ── Disponibilité ──────────────────────────────────
        # Le stock du catalogue est fictif (50 unités posées en masse) : tant que le
        # paramètre « stock_reel » n'est pas activé, tout est traité comme expédié par
        # le fournisseur, avec son délai réel.
        stock_reel = Liv._param('stock_reel', '') == 'True'
        qty = product.virtual_available if stock_reel else 0
        delai = Liv.delai_fournisseur(tmpl)
        if stock_reel and qty > 0:
            delai = Liv._param('delai_stock', 1)
            stock_label = tr(lg, 'En stock', 'Op voorraad', 'In stock') if qty > 10 else tr(
                lg, 'Plus que %d en stock', 'Nog %d op voorraad', 'Only %d left in stock') % int(qty)
            stock_class = 'lp-stock-green' if qty > 10 else 'lp-stock-orange'
            stock_sub = tr(lg, '— expédié depuis Boninne', '— verzonden vanuit Boninne', '— shipped from Boninne')
        else:
            stock_label = tr(lg, 'Disponible', 'Beschikbaar', 'Available')
            stock_class = 'lp-stock-green'
            stock_sub = ''

        # ── Livraison estimée ──────────────────────────────
        promesse = Liv.promesse(delai)
        delivery_str = promesse['texte']

        # ── Marque : uniquement la vraie marque, jamais le distributeur ──
        BRAND_BLACKLIST = {
            'scp', 'scp benelux', 'sibo', 'benelux',
            'fluidra', 'fluidra benelux',
        }
        brand = ''
        for line in tmpl.attribute_line_ids:
            if 'marque' in (line.attribute_id.name or '').lower():
                vals = line.product_template_value_ids.filtered(lambda v: v.ptav_active)
                if vals and vals[0].name and vals[0].name.strip().lower() not in BRAND_BLACKLIST:
                    brand = vals[0].name
                break
        # Pas de fallback seller_ids : si pas de vraie marque, brand reste vide
        # → le JS (if info.brand) laisse la ligne « Marque » masquée.

        # ── Garantie ──────────────────────────────────────
        warranty = ''
        for line in tmpl.attribute_line_ids:
            if 'garantie' in (line.attribute_id.name or '').lower():
                vals = line.product_template_value_ids.filtered(lambda v: v.ptav_active)
                if vals:
                    warranty = vals[0].name
                    break
        if not warranty:
            desc = (tmpl.description_sale or '') + (tmpl.description or '')
            m = re.search(r'(\d+)\s*an', desc, re.IGNORECASE)
            if m:
                n = int(m.group(1))
                warranty = '%d %s' % (n, tr(lg, 'an' if n == 1 else 'ans', 'jaar', 'year' if n == 1 else 'years'))

        # ── Livraison offerte ─────────────────────────────
        seuil, base = Liv.seuil_franco(request.website)
        price = product.lst_price or tmpl.list_price or 0.0
        free_delivery = price >= seuil

        return {
            'stock_label':  stock_label,
            'stock_class':  stock_class,
            'stock_qty':    int(qty),
            'stock_sub':    stock_sub,
            'delivery':     delivery_str,
            'countdown':    promesse['compte_a_rebours'],
            'franco_txt':   tr(lg, 'Offerte dès %s', 'Gratis vanaf %s', 'Free from %s') % Liv.franco_texte(request.website),
            'free_txt':     tr(lg, 'Offerte', 'Gratis', 'Free'),
            'free_badge':   tr(lg, 'GRATUITE', 'GRATIS', 'FREE'),
            'warranty_txt': tr(lg, 'Garantie', 'Garantie', 'Warranty'),
            'brand':        brand,
            'warranty':     warranty,
            'default_code': product.default_code or tmpl.default_code or '',
            'free_delivery': free_delivery,
        }
