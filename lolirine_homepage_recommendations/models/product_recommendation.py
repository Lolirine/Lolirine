# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, timedelta
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)


class ProductRecommendation(models.Model):
    """
    Service de recommandation de produits.
    Fournit différents algorithmes de recommandation.

    ⚠️ EXCLUSIVEMENT POUR LE SITE LOLIRINE POOL
    Toutes les requêtes sont filtrées par website_id.
    """
    _name = 'product.recommendation'
    _description = 'Service de Recommandation Produits - Lolirine Pool'
    _auto = False  # Pas de table, juste des méthodes

    def _get_lolirine_pool_website_id(self):
        param = self.env['ir.config_parameter'].sudo()
        website_id = param.get_param('lolirine_pool.website_id', default='0')
        return int(website_id) if website_id else 0

    def _get_published_products_domain(self, website_id=None):
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        domain = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
        ]
        if pool_website_id:
            domain.append(('website_id', 'in', [False, pool_website_id]))
        return domain

    def _get_fallback_products(self, limit=12, website_id=None, category_id=None, order='create_date desc'):
        """
        Fallback générique : retourne des produits publiés triés par ordre donné.
        Utilisé quand les algorithmes spécialisés ne trouvent rien.
        """
        domain = self._get_published_products_domain(website_id)
        if category_id:
            domain.append(('public_categ_ids', 'in', [category_id]))
        templates = self.env['product.template'].search(domain, order=order, limit=limit)
        products = templates.mapped('product_variant_ids').filtered(lambda p: p.is_published)
        return products[:limit]

    @api.model
    def get_recently_viewed(self, visitor_id=None, partner_id=None, session_id=None, limit=12, website_id=None):
        Activity = self.env['visitor.product.activity']
        pool_website_id = website_id or self._get_lolirine_pool_website_id()

        domain = [('activity_type', '=', 'view')]
        if pool_website_id:
            domain.append(('website_id', '=', pool_website_id))

        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        elif visitor_id:
            domain.append(('visitor_id', '=', visitor_id))
        elif session_id:
            domain.append(('session_id', '=', session_id))
        else:
            return self.env['product.product']

        activities = Activity.search(domain, order='last_view_date desc', limit=limit)
        products = activities.mapped('product_id').filtered(
            lambda p: p.is_published and p.sale_ok
        )
        return products[:limit]

    @api.model
    def get_continue_shopping(self, partner_id, limit=12, website_id=None):
        products = self.env['product.product']
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        SaleOrder = self.env['sale.order']

        cart_domain = [
            ('partner_id', '=', partner_id),
            ('state', '=', 'draft'),
            ('create_date', '>=', datetime.now() - timedelta(days=30)),
        ]
        if pool_website_id:
            cart_domain.append(('website_id', '=', pool_website_id))

        abandoned_carts = SaleOrder.search(cart_domain, limit=5)
        cart_products = abandoned_carts.mapped('order_line.product_id').filtered(
            lambda p: p.is_published and p.sale_ok
        )
        products |= cart_products

        order_domain = [
            ('partner_id', '=', partner_id),
            ('state', 'in', ['sale', 'done']),
        ]
        if pool_website_id:
            order_domain.append(('website_id', '=', pool_website_id))

        recent_orders = SaleOrder.search(order_domain, order='date_order desc', limit=5)
        purchased_categories = recent_orders.mapped('order_line.product_id.product_tmpl_id.public_categ_ids')
        if purchased_categories:
            category_products = self.env['product.template'].search([
                ('public_categ_ids', 'in', purchased_categories.ids),
                ('is_published', '=', True),
                ('sale_ok', '=', True),
                ('id', 'not in', recent_orders.mapped('order_line.product_id.product_tmpl_id').ids),
            ] + ([('website_id', 'in', [False, pool_website_id])] if pool_website_id else []),
                limit=limit)
            products |= category_products.mapped('product_variant_ids').filtered(
                lambda p: p.is_published
            )

        return products[:limit]

    @api.model
    def get_best_sellers(self, limit=12, days=30, website_id=None, category_id=None):
        """
        Retourne les produits les plus vendus sur Lolirine Pool.
        Fallback : produits publiés triés par prix décroissant si pas de ventes.
        """
        date_from = datetime.now() - timedelta(days=days)
        pool_website_id = website_id or self._get_lolirine_pool_website_id()

        website_filter = f"AND so.website_id = {pool_website_id}" if pool_website_id else ""
        category_filter = ""
        if category_id:
            category_filter = f"""AND EXISTS (
                SELECT 1 FROM product_public_category_product_template_rel ppcptr
                WHERE ppcptr.product_template_id = pt.id
                AND ppcptr.product_public_category_id = {int(category_id)}
            )"""

        self.env.cr.execute(f"""
            SELECT sol.product_id, SUM(sol.product_uom_qty) as qty
            FROM sale_order_line sol
            JOIN sale_order so ON sol.order_id = so.id
            JOIN product_product pp ON sol.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE so.state IN ('sale', 'done')
              AND so.date_order >= %s
              AND pt.is_published = true
              AND pt.sale_ok = true
              {website_filter}
              {category_filter}
            GROUP BY sol.product_id
            ORDER BY qty DESC
            LIMIT %s
        """, [date_from, limit])

        results = self.env.cr.fetchall()
        product_ids = [r[0] for r in results]

        if product_ids:
            return self.env['product.product'].browse(product_ids)

        # Fallback : produits les plus chers (proxy de popularité pour un nouveau catalogue)
        _logger.info("get_best_sellers: pas de ventes, fallback prix décroissant")
        return self._get_fallback_products(limit=limit, website_id=pool_website_id,
                                           category_id=category_id, order='list_price desc')

    @api.model
    def get_top_rated(self, limit=12, min_rating=4.0, website_id=None, category_id=None):
        """
        Retourne les produits les mieux notés sur Lolirine Pool.
        Fallback : si pas de ratings, retourne des produits récents.
        """
        pool_website_id = website_id or self._get_lolirine_pool_website_id()

        domain = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
            ('rating_avg', '>=', min_rating),
            ('rating_count', '>', 0),
        ]
        if pool_website_id:
            domain.append(('website_id', 'in', [False, pool_website_id]))
        if category_id:
            domain.append(('public_categ_ids', 'in', [category_id]))

        templates = self.env['product.template'].search(
            domain,
            order='rating_avg desc, rating_count desc',
            limit=limit
        )
        products = templates.mapped('product_variant_ids').filtered(lambda p: p.is_published)

        if products:
            return products[:limit]

        # Fallback : produits avec le nom le plus court (souvent produits phares)
        # en pratique : tri par write_date desc pour avoir les produits récemment mis à jour
        _logger.info("get_top_rated: pas de ratings, fallback write_date desc")
        return self._get_fallback_products(limit=limit, website_id=pool_website_id,
                                           category_id=category_id, order='write_date desc')

    @api.model
    def get_promotions(self, limit=12, website_id=None, category_id=None):
        """
        Retourne les produits en promotion sur Lolirine Pool.
        Fallback : produits avec ribbon 'Promo' dans lolirine_pool_promos,
        sinon produits aléatoires récents.
        """
        pool_website_id = website_id or self._get_lolirine_pool_website_id()

        domain = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
        ]
        if pool_website_id:
            domain.append(('website_id', 'in', [False, pool_website_id]))
        if category_id:
            domain.append(('public_categ_ids', 'in', [category_id]))

        templates = self.env['product.template'].search(domain, limit=limit * 5)

        promotion_products = []
        for tmpl in templates:
            product = tmpl.product_variant_ids[:1]
            if not product:
                continue
            if tmpl.compare_list_price and tmpl.compare_list_price > tmpl.list_price:
                discount_pct = ((tmpl.compare_list_price - tmpl.list_price) / tmpl.compare_list_price) * 100
                promotion_products.append((product, discount_pct))

        if promotion_products:
            promotion_products.sort(key=lambda x: x[1], reverse=True)
            return self.env['product.product'].browse([p[0].id for p in promotion_products[:limit]])

        # Fallback 1 : chercher les produits avec un ribbon 'Promo' (lolirine_pool_promos)
        try:
            promo_domain = [
                ('is_published', '=', True),
                ('sale_ok', '=', True),
                ('website_ribbon_id.html', 'ilike', 'Promo'),
            ]
            if pool_website_id:
                promo_domain.append(('website_id', 'in', [False, pool_website_id]))
            ribbon_templates = self.env['product.template'].search(promo_domain, limit=limit)
            if ribbon_templates:
                products = ribbon_templates.mapped('product_variant_ids').filtered(lambda p: p.is_published)
                if products:
                    return products[:limit]
        except Exception:
            pass

        # Fallback 2 : produits récents comme "nouveautés promotionnelles"
        _logger.info("get_promotions: pas de promotions, fallback nouveautés")
        return self._get_fallback_products(limit=limit, website_id=pool_website_id,
                                           category_id=category_id, order='create_date desc')

    @api.model
    def get_new_arrivals(self, limit=12, days=90, website_id=None, category_id=None):
        """
        Retourne les nouveaux produits sur Lolirine Pool.
        Fallback : élargit la fenêtre temporelle si pas de résultats.
        """
        pool_website_id = website_id or self._get_lolirine_pool_website_id()

        for window_days in [days, 180, 365, 3650]:
            date_from = datetime.now() - timedelta(days=window_days)
            domain = [
                ('is_published', '=', True),
                ('sale_ok', '=', True),
                ('create_date', '>=', date_from),
            ]
            if pool_website_id:
                domain.append(('website_id', 'in', [False, pool_website_id]))
            if category_id:
                domain.append(('public_categ_ids', 'in', [category_id]))

            templates = self.env['product.template'].search(
                domain, order='create_date desc', limit=limit
            )
            products = templates.mapped('product_variant_ids').filtered(lambda p: p.is_published)
            if products:
                return products[:limit]

        # Fallback final
        return self._get_fallback_products(limit=limit, website_id=pool_website_id,
                                           category_id=category_id, order='id desc')

    @api.model
    def get_frequently_bought_together(self, product_id, limit=6, website_id=None):
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        website_filter = f"AND so.website_id = {pool_website_id}" if pool_website_id else ""

        self.env.cr.execute(f"""
            WITH target_orders AS (
                SELECT DISTINCT sol.order_id
                FROM sale_order_line sol
                JOIN sale_order so ON sol.order_id = so.id
                WHERE sol.product_id = %s
                  AND so.state IN ('sale', 'done')
                  {website_filter}
            )
            SELECT sol.product_id, COUNT(*) as freq
            FROM sale_order_line sol
            JOIN target_orders to_orders ON sol.order_id = to_orders.order_id
            JOIN product_product pp ON sol.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE sol.product_id != %s
              AND pt.is_published = true
              AND pt.sale_ok = true
            GROUP BY sol.product_id
            ORDER BY freq DESC
            LIMIT %s
        """, [product_id, product_id, limit])

        results = self.env.cr.fetchall()
        product_ids = [r[0] for r in results]

        if product_ids:
            return self.env['product.product'].browse(product_ids)

        # Fallback : produits de la même catégorie
        product = self.env['product.product'].browse(product_id)
        if product.exists():
            categories = product.product_tmpl_id.public_categ_ids
            if categories:
                domain = [
                    ('is_published', '=', True),
                    ('sale_ok', '=', True),
                    ('public_categ_ids', 'in', categories.ids),
                    ('product_variant_ids', '!=', product_id),
                ]
                if pool_website_id:
                    domain.append(('website_id', 'in', [False, pool_website_id]))
                templates = self.env['product.template'].search(domain, limit=limit)
                return templates.mapped('product_variant_ids').filtered(
                    lambda p: p.is_published and p.id != product_id
                )[:limit]

        return self.env['product.product']

    @api.model
    def get_related_to_viewed(self, visitor_id=None, partner_id=None, session_id=None, limit=12, website_id=None):
        pool_website_id = website_id or self._get_lolirine_pool_website_id()

        recently_viewed = self.get_recently_viewed(
            visitor_id=visitor_id,
            partner_id=partner_id,
            session_id=session_id,
            limit=5,
            website_id=pool_website_id
        )

        if not recently_viewed:
            return self.env['product.product']

        viewed_categories = recently_viewed.mapped('product_tmpl_id.public_categ_ids')
        viewed_product_ids = recently_viewed.ids

        if not viewed_categories:
            return self.env['product.product']

        domain = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
            ('public_categ_ids', 'in', viewed_categories.ids),
            ('product_variant_ids', 'not in', viewed_product_ids),
        ]
        if pool_website_id:
            domain.append(('website_id', 'in', [False, pool_website_id]))

        templates = self.env['product.template'].search(
            domain,
            order='write_date desc',
            limit=limit
        )
        products = templates.mapped('product_variant_ids').filtered(
            lambda p: p.is_published and p.id not in viewed_product_ids
        )
        return products[:limit]

    @api.model
    def get_personalized_for_category(self, category_id, visitor_id=None, partner_id=None, limit=12, website_id=None):
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        products = self.env['product.product']

        best_sellers = self.get_best_sellers(
            limit=int(limit * 0.4) or 1,
            category_id=category_id,
            website_id=pool_website_id
        )
        products |= best_sellers

        top_rated = self.get_top_rated(
            limit=int(limit * 0.3) or 1,
            category_id=category_id,
            website_id=pool_website_id
        )
        products |= top_rated.filtered(lambda p: p.id not in products.ids)

        new_arrivals = self.get_new_arrivals(
            limit=int(limit * 0.3) or 1,
            category_id=category_id,
            website_id=pool_website_id
        )
        products |= new_arrivals.filtered(lambda p: p.id not in products.ids)

        return products[:limit]

    @api.model
    def get_all_recommendations(self, visitor_id=None, partner_id=None, session_id=None, website_id=None):
        recommendations = {}
        pool_website_id = website_id or self._get_lolirine_pool_website_id()

        recently_viewed = self.get_recently_viewed(
            visitor_id=visitor_id,
            partner_id=partner_id,
            session_id=session_id,
            website_id=pool_website_id
        )
        if recently_viewed:
            recommendations['recently_viewed'] = {
                'title': 'Produits récemment consultés',
                'products': recently_viewed,
                'icon': 'fa-history',
            }

        if partner_id:
            continue_shopping = self.get_continue_shopping(
                partner_id=partner_id,
                website_id=pool_website_id
            )
            if continue_shopping:
                recommendations['continue_shopping'] = {
                    'title': 'Continuez vos achats',
                    'products': continue_shopping,
                    'icon': 'fa-shopping-cart',
                }

        related_to_viewed = self.get_related_to_viewed(
            visitor_id=visitor_id,
            partner_id=partner_id,
            session_id=session_id,
            website_id=pool_website_id
        )
        if related_to_viewed:
            recommendations['related_to_viewed'] = {
                'title': 'En lien avec vos consultations',
                'products': related_to_viewed,
                'icon': 'fa-link',
            }

        best_sellers = self.get_best_sellers(website_id=pool_website_id)
        if best_sellers:
            recommendations['best_sellers'] = {
                'title': 'Meilleures ventes',
                'products': best_sellers,
                'icon': 'fa-fire',
            }

        top_rated = self.get_top_rated(website_id=pool_website_id)
        if top_rated:
            recommendations['top_rated'] = {
                'title': 'Les mieux notés',
                'subtitle': '4 étoiles et plus',
                'products': top_rated,
                'icon': 'fa-star',
            }

        promotions = self.get_promotions(website_id=pool_website_id)
        if promotions:
            recommendations['promotions'] = {
                'title': 'Offres du moment',
                'products': promotions,
                'icon': 'fa-tags',
                'badge': 'Promo',
            }

        new_arrivals = self.get_new_arrivals(website_id=pool_website_id)
        if new_arrivals:
            recommendations['new_arrivals'] = {
                'title': 'Nouveautés',
                'products': new_arrivals,
                'icon': 'fa-certificate',
                'badge': 'Nouveau',
            }

        if partner_id or visitor_id:
            Preference = self.env['visitor.category.preference']
            pref_domain = []
            if partner_id:
                pref_domain.append(('partner_id', '=', partner_id))
            elif visitor_id:
                pref_domain.append(('visitor_id', '=', visitor_id))

            top_categories = Preference.search(pref_domain, order='score desc', limit=3)
            for i, pref in enumerate(top_categories):
                cat_products = self.get_personalized_for_category(
                    category_id=pref.category_id.id,
                    visitor_id=visitor_id,
                    partner_id=partner_id,
                    website_id=pool_website_id
                )
                if cat_products:
                    recommendations[f'category_{i}'] = {
                        'title': f'Pour vous dans {pref.category_id.name}',
                        'products': cat_products,
                        'icon': 'fa-folder-open',
                        'category_id': pref.category_id.id,
                    }

        return recommendations
