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
        """
        Récupère l'ID du website Lolirine Pool depuis la configuration.
        """
        param = self.env['ir.config_parameter'].sudo()
        website_id = param.get_param('lolirine_pool.website_id', default='0')
        return int(website_id) if website_id else 0

    def _get_published_products_domain(self, website_id=None):
        """
        Retourne le domaine de base pour les produits publiés sur Lolirine Pool.
        """
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        domain = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
        ]
        
        # Filtrer par website si configuré
        if pool_website_id:
            # Les produits doivent être disponibles sur ce website
            domain.append(('website_id', 'in', [False, pool_website_id]))
        
        return domain

    @api.model
    def get_recently_viewed(self, visitor_id=None, partner_id=None, session_id=None, limit=12, website_id=None):
        """
        Retourne les produits récemment consultés par le visiteur sur Lolirine Pool.
        """
        Activity = self.env['visitor.product.activity']
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        domain = [('activity_type', '=', 'view')]
        
        # IMPORTANT: Filtrer par le website Lolirine Pool
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
        """
        Retourne des produits pour "Continuer vos achats" sur Lolirine Pool basé sur:
        - Produits ajoutés au panier mais non achetés
        - Produits dans les mêmes catégories que les achats récents
        """
        products = self.env['product.product']
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        # 1. Produits dans les paniers abandonnés SUR LE SITE POOL
        SaleOrder = self.env['sale.order']
        
        cart_domain = [
            ('partner_id', '=', partner_id),
            ('state', '=', 'draft'),
            ('create_date', '>=', datetime.now() - timedelta(days=30)),
        ]
        
        # IMPORTANT: Filtrer par website Lolirine Pool
        if pool_website_id:
            cart_domain.append(('website_id', '=', pool_website_id))
        
        abandoned_carts = SaleOrder.search(cart_domain, limit=5)
        
        cart_products = abandoned_carts.mapped('order_line.product_id').filtered(
            lambda p: p.is_published and p.sale_ok
        )
        products |= cart_products
        
        # 2. Produits des mêmes catégories que les achats récents SUR LE SITE POOL
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
        """
        date_from = datetime.now() - timedelta(days=days)
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        # IMPORTANT: Filtrer les ventes par website Lolirine Pool
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
        
        # Garder l'ordre
        products = self.env['product.product'].browse(product_ids)
        return products

    @api.model
    def get_top_rated(self, limit=12, min_rating=4.0, website_id=None, category_id=None):
        """
        Retourne les produits les mieux notés sur Lolirine Pool.
        """
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        domain = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
            ('rating_avg', '>=', min_rating),
            ('rating_count', '>', 0),
        ]
        
        # IMPORTANT: Filtrer par website Lolirine Pool
        if pool_website_id:
            domain.append(('website_id', 'in', [False, pool_website_id]))
        
        if category_id:
            domain.append(('public_categ_ids', 'in', [category_id]))
        
        templates = self.env['product.template'].search(
            domain, 
            order='rating_avg desc, rating_count desc',
            limit=limit
        )
        
        products = templates.mapped('product_variant_ids').filtered(
            lambda p: p.is_published
        )
        
        return products[:limit]

    @api.model
    def get_promotions(self, limit=12, website_id=None, category_id=None):
        """
        Retourne les produits en promotion sur Lolirine Pool.
        """
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        domain = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
        ]
        
        # IMPORTANT: Filtrer par website Lolirine Pool
        if pool_website_id:
            domain.append(('website_id', 'in', [False, pool_website_id]))
        
        if category_id:
            domain.append(('public_categ_ids', 'in', [category_id]))
        
        templates = self.env['product.template'].search(domain, limit=limit * 2)
        
        promotion_products = []
        for tmpl in templates:
            product = tmpl.product_variant_ids[:1]
            if not product:
                continue
            
            # Vérifier s'il y a une réduction
            if tmpl.compare_list_price and tmpl.compare_list_price > tmpl.list_price:
                discount_pct = ((tmpl.compare_list_price - tmpl.list_price) / tmpl.compare_list_price) * 100
                promotion_products.append((product, discount_pct))
        
        # Trier par pourcentage de réduction
        promotion_products.sort(key=lambda x: x[1], reverse=True)
        
        return self.env['product.product'].browse([p[0].id for p in promotion_products[:limit]])

    @api.model
    def get_new_arrivals(self, limit=12, days=30, website_id=None, category_id=None):
        """
        Retourne les nouveaux produits sur Lolirine Pool.
        """
        date_from = datetime.now() - timedelta(days=days)
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        domain = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
            ('create_date', '>=', date_from),
        ]
        
        # IMPORTANT: Filtrer par website Lolirine Pool
        if pool_website_id:
            domain.append(('website_id', 'in', [False, pool_website_id]))
        
        if category_id:
            domain.append(('public_categ_ids', 'in', [category_id]))
        
        templates = self.env['product.template'].search(
            domain,
            order='create_date desc',
            limit=limit
        )
        
        products = templates.mapped('product_variant_ids').filtered(
            lambda p: p.is_published
        )
        
        return products[:limit]

    @api.model
    def get_frequently_bought_together(self, product_id, limit=6, website_id=None):
        """
        Retourne les produits fréquemment achetés avec un produit donné sur Lolirine Pool.
        """
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        # IMPORTANT: Filtrer par website Lolirine Pool
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
        
        return self.env['product.product'].browse(product_ids)

    @api.model
    def get_related_to_viewed(self, visitor_id=None, partner_id=None, session_id=None, limit=12, website_id=None):
        """
        Retourne des produits liés aux produits consultés sur Lolirine Pool.
        """
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        # D'abord, obtenir les produits récemment vus
        recently_viewed = self.get_recently_viewed(
            visitor_id=visitor_id,
            partner_id=partner_id,
            session_id=session_id,
            limit=5,
            website_id=pool_website_id
        )
        
        if not recently_viewed:
            return self.env['product.product']
        
        # Obtenir les catégories des produits vus
        viewed_categories = recently_viewed.mapped('product_tmpl_id.public_categ_ids')
        viewed_product_ids = recently_viewed.ids
        
        if not viewed_categories:
            return self.env['product.product']
        
        # Chercher des produits similaires dans les mêmes catégories
        domain = [
            ('is_published', '=', True),
            ('sale_ok', '=', True),
            ('public_categ_ids', 'in', viewed_categories.ids),
            ('product_variant_ids', 'not in', viewed_product_ids),
        ]
        
        # IMPORTANT: Filtrer par website Lolirine Pool
        if pool_website_id:
            domain.append(('website_id', 'in', [False, pool_website_id]))
        
        templates = self.env['product.template'].search(
            domain,
            order='rating_avg desc, create_date desc',
            limit=limit
        )
        
        products = templates.mapped('product_variant_ids').filtered(
            lambda p: p.is_published and p.id not in viewed_product_ids
        )
        
        return products[:limit]

    @api.model
    def get_personalized_for_category(self, category_id, visitor_id=None, partner_id=None, limit=12, website_id=None):
        """
        Retourne des produits personnalisés pour une catégorie donnée sur Lolirine Pool.
        Combine plusieurs signaux: popularité, nouveauté, notes.
        """
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        # Mélanger différentes sources
        products = self.env['product.product']
        
        # 1. Best sellers dans la catégorie (40%)
        best_sellers = self.get_best_sellers(
            limit=int(limit * 0.4),
            category_id=category_id,
            website_id=pool_website_id
        )
        products |= best_sellers
        
        # 2. Top rated dans la catégorie (30%)
        top_rated = self.get_top_rated(
            limit=int(limit * 0.3),
            category_id=category_id,
            website_id=pool_website_id
        )
        products |= top_rated.filtered(lambda p: p.id not in products.ids)
        
        # 3. Nouveautés dans la catégorie (30%)
        new_arrivals = self.get_new_arrivals(
            limit=int(limit * 0.3),
            category_id=category_id,
            website_id=pool_website_id
        )
        products |= new_arrivals.filtered(lambda p: p.id not in products.ids)
        
        return products[:limit]

    @api.model
    def get_all_recommendations(self, visitor_id=None, partner_id=None, session_id=None, website_id=None):
        """
        Retourne toutes les recommandations pour affichage sur la homepage Lolirine Pool.
        """
        recommendations = {}
        pool_website_id = website_id or self._get_lolirine_pool_website_id()
        
        # 1. Produits récemment consultés
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
        
        # 2. Continuez vos achats (si connecté)
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
        
        # 3. En lien avec vos consultations
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
        
        # 4. Meilleures ventes
        best_sellers = self.get_best_sellers(website_id=pool_website_id)
        if best_sellers:
            recommendations['best_sellers'] = {
                'title': 'Meilleures ventes',
                'products': best_sellers,
                'icon': 'fa-fire',
            }
        
        # 5. Produits les mieux notés
        top_rated = self.get_top_rated(website_id=pool_website_id)
        if top_rated:
            recommendations['top_rated'] = {
                'title': 'Les mieux notés',
                'subtitle': '4 étoiles et plus',
                'products': top_rated,
                'icon': 'fa-star',
            }
        
        # 6. Offres et promotions
        promotions = self.get_promotions(website_id=pool_website_id)
        if promotions:
            recommendations['promotions'] = {
                'title': 'Offres du moment',
                'products': promotions,
                'icon': 'fa-tags',
                'badge': 'Promo',
            }
        
        # 7. Nouveautés
        new_arrivals = self.get_new_arrivals(website_id=pool_website_id)
        if new_arrivals:
            recommendations['new_arrivals'] = {
                'title': 'Nouveautés',
                'products': new_arrivals,
                'icon': 'fa-certificate',
                'badge': 'Nouveau',
            }
        
        # 8. Recommandations par catégorie préférée
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
