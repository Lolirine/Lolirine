from odoo import http
from odoo.http import request
from collections import defaultdict


class BuyAgainController(http.Controller):

    @http.route('/shop/acheter-a-nouveau', type='http', auth='user',
                website=True, sitemap=True)
    def buy_again(self, category=None, sort='recent', search='', **kwargs):
        """
        Page 'Acheter à nouveau' — liste les produits déjà commandés
        par le client connecté, groupés par date de commande.
        """
        partner = request.env.user.partner_id

        # ── Récupérer les commandes confirmées du client ──────
        orders = request.env['sale.order'].sudo().search([
            ('partner_id', 'child_of', partner.id),
            ('state', 'in', ['sale', 'done']),
            ('website_id', '=', request.website.id),
        ], order='date_order desc', limit=50)

        # ── Construire la liste de produits uniques ───────────
        seen_tmpl = set()
        products = []

        for order in orders:
            for line in order.order_line:
                tmpl = line.product_id.product_tmpl_id
                if not tmpl or tmpl.id in seen_tmpl:
                    continue
                if not tmpl.active or not tmpl.website_published:
                    continue
                seen_tmpl.add(tmpl.id)
                products.append({
                    'tmpl':        tmpl,
                    'variant':     line.product_id,
                    'last_order':  order,
                    'last_date':   order.date_order,
                    'qty_ordered': line.product_uom_qty,
                    'price_unit':  line.price_unit,
                })

        # ── Filtrer par catégorie publique ────────────────────
        all_categories = {}
        for p in products:
            for cat in p['tmpl'].public_categ_ids:
                all_categories[cat.id] = cat.name

        if category:
            try:
                cat_id = int(category)
                products = [
                    p for p in products
                    if cat_id in p['tmpl'].public_categ_ids.ids
                ]
            except (ValueError, TypeError):
                pass

        # ── Filtrer par recherche ─────────────────────────────
        if search:
            s = search.lower()
            products = [
                p for p in products
                if s in (p['tmpl'].name or '').lower()
            ]

        # ── Trier ─────────────────────────────────────────────
        if sort == 'price_asc':
            products.sort(key=lambda p: p['tmpl'].list_price or 0)
        elif sort == 'price_desc':
            products.sort(key=lambda p: -(p['tmpl'].list_price or 0))
        elif sort == 'name':
            products.sort(key=lambda p: p['tmpl'].name or '')
        # 'recent' = ordre par défaut (déjà trié par date_order desc)

        return request.render('lolirine_pool_buyagain.page_buy_again', {
            'products':        products,
            'all_categories':  all_categories,
            'current_category': int(category) if category else None,
            'current_sort':    sort,
            'search':          search,
            'orders_count':    len(orders),
        })
