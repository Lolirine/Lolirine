# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class HomepageRecommendationsController(http.Controller):
    """
    Controller pour les recommandations de la page d'accueil.
    Fournit des endpoints pour le tracking et la récupération des recommandations.
    
    ⚠️ EXCLUSIVEMENT POUR LE SITE LOLIRINE POOL
    """

    def _get_lolirine_pool_website_id(self):
        param = request.env['ir.config_parameter'].sudo()
        website_id = param.get_param('lolirine_pool.website_id', default='0')
        return int(website_id) if website_id else 0

    def _is_lolirine_pool_website(self):
        if not hasattr(request, 'website') or not request.website:
            return False
        pool_website_id = self._get_lolirine_pool_website_id()
        if pool_website_id == 0:
            param = request.env['ir.config_parameter'].sudo()
            pool_domain = param.get_param('lolirine_pool.domain', default='pool.lolirine.be')
            current_domain = request.website.domain or ''
            return pool_domain.lower() in current_domain.lower()
        return request.website.id == pool_website_id

    def _get_visitor_info(self):
        visitor_id = None
        partner_id = None
        session_id = request.session.sid
        if request.env.user and not request.env.user._is_public():
            partner_id = request.env.user.partner_id.id
        visitor = request.env['website.visitor']._get_visitor_from_request()
        if visitor:
            visitor_id = visitor.id
        website_id = self._get_lolirine_pool_website_id()
        if website_id == 0 and hasattr(request, 'website') and request.website:
            website_id = request.website.id
        return {
            'visitor_id': visitor_id,
            'partner_id': partner_id,
            'session_id': session_id,
            'website_id': website_id,
        }

    @http.route('/shop/track/view', type='jsonrpc', auth='public', website=True)
    def track_product_view(self, product_id, is_template=False):
        if not self._is_lolirine_pool_website():
            return {'success': False, 'error': 'Not on Lolirine Pool website'}
        try:
            visitor_info = self._get_visitor_info()
            Activity = request.env['visitor.product.activity'].sudo()
            actual_product_id = int(product_id)
            if is_template:
                template = request.env['product.template'].sudo().browse(actual_product_id)
                if template.exists() and template.product_variant_ids:
                    actual_product_id = template.product_variant_ids[0].id
                else:
                    return {'success': False, 'error': 'Template not found or has no variants'}
            else:
                product = request.env['product.product'].sudo().browse(actual_product_id)
                if not product.exists():
                    template = request.env['product.template'].sudo().browse(actual_product_id)
                    if template.exists() and template.product_variant_ids:
                        actual_product_id = template.product_variant_ids[0].id
                    else:
                        return {'success': False, 'error': 'Product not found'}
            activity = Activity.log_product_view(
                product_id=actual_product_id,
                visitor_id=visitor_info['visitor_id'],
                partner_id=visitor_info['partner_id'],
                session_id=visitor_info['session_id'],
                website_id=visitor_info['website_id'],
            )
            return {'success': True, 'activity_id': activity.id if activity else None}
        except Exception as e:
            _logger.error(f"Erreur tracking vue produit: {e}")
            return {'success': False, 'error': str(e)}

    @http.route('/shop/recommendations', type='jsonrpc', auth='public', website=True)
    def get_recommendations(self, section=None, limit=12, category_id=None):
        if not self._is_lolirine_pool_website():
            return {'success': False, 'error': 'Not on Lolirine Pool website', 'products': []}
        try:
            visitor_info = self._get_visitor_info()
            Recommendation = request.env['product.recommendation'].sudo()
            products = request.env['product.product']
            title = ""
            subtitle = ""
            icon = ""
            badge = ""
            if section == 'recently_viewed':
                products = Recommendation.get_recently_viewed(
                    visitor_id=visitor_info['visitor_id'],
                    partner_id=visitor_info['partner_id'],
                    session_id=visitor_info['session_id'],
                    limit=limit,
                    website_id=visitor_info['website_id'],
                )
                title = "Produits récemment consultés"
                icon = "fa-history"
            elif section == 'continue_shopping':
                if visitor_info['partner_id']:
                    products = Recommendation.get_continue_shopping(
                        partner_id=visitor_info['partner_id'],
                        limit=limit,
                        website_id=visitor_info['website_id'],
                    )
                title = "Continuez vos achats"
                icon = "fa-shopping-cart"
            elif section == 'related_to_viewed':
                products = Recommendation.get_related_to_viewed(
                    visitor_id=visitor_info['visitor_id'],
                    partner_id=visitor_info['partner_id'],
                    session_id=visitor_info['session_id'],
                    limit=limit,
                    website_id=visitor_info['website_id'],
                )
                title = "En lien avec vos consultations"
                icon = "fa-link"
            elif section == 'best_sellers':
                products = Recommendation.get_best_sellers(
                    limit=limit,
                    website_id=visitor_info['website_id'],
                    category_id=category_id,
                )
                title = "Meilleures ventes"
                icon = "fa-fire"
            elif section == 'top_rated':
                products = Recommendation.get_top_rated(
                    limit=limit,
                    website_id=visitor_info['website_id'],
                    category_id=category_id,
                )
                title = "Les mieux notés"
                subtitle = "4 étoiles et plus"
                icon = "fa-star"
            elif section == 'promotions':
                products = Recommendation.get_promotions(
                    limit=limit,
                    website_id=visitor_info['website_id'],
                    category_id=category_id,
                )
                title = "Offres du moment"
                icon = "fa-tags"
                badge = "Promo"
            elif section == 'new_arrivals':
                products = Recommendation.get_new_arrivals(
                    limit=limit,
                    website_id=visitor_info['website_id'],
                    category_id=category_id,
                )
                title = "Nouveautés"
                icon = "fa-certificate"
                badge = "Nouveau"
            elif section == 'for_category' and category_id:
                products = Recommendation.get_personalized_for_category(
                    category_id=category_id,
                    visitor_id=visitor_info['visitor_id'],
                    partner_id=visitor_info['partner_id'],
                    limit=limit,
                    website_id=visitor_info['website_id'],
                )
                category = request.env['product.public.category'].browse(category_id)
                title = f"Pour vous dans {category.name}"
                icon = "fa-folder-open"
            elif section == 'frequently_bought_together':
                pass
            products_data = self._format_products(products)
            return {
                'success': True,
                'title': title,
                'subtitle': subtitle,
                'icon': icon,
                'badge': badge,
                'products': products_data,
                'count': len(products_data),
            }
        except Exception as e:
            _logger.error(f"Erreur récupération recommandations: {e}")
            return {'success': False, 'error': str(e), 'products': []}

    @http.route('/shop/recommendations/all', type='jsonrpc', auth='public', website=True)
    def get_all_recommendations(self):
        if not self._is_lolirine_pool_website():
            return {'success': False, 'error': 'Not on Lolirine Pool website', 'recommendations': {}}
        try:
            visitor_info = self._get_visitor_info()
            Recommendation = request.env['product.recommendation'].sudo()
            all_recs = Recommendation.get_all_recommendations(
                visitor_id=visitor_info['visitor_id'],
                partner_id=visitor_info['partner_id'],
                session_id=visitor_info['session_id'],
                website_id=visitor_info['website_id'],
            )
            result = {}
            for key, data in all_recs.items():
                result[key] = {
                    'title': data.get('title', ''),
                    'subtitle': data.get('subtitle', ''),
                    'icon': data.get('icon', ''),
                    'badge': data.get('badge', ''),
                    'products': self._format_products(data.get('products', [])),
                    'category_id': data.get('category_id'),
                }
            return {'success': True, 'recommendations': result}
        except Exception as e:
            _logger.error(f"Erreur récupération toutes recommandations: {e}")
            return {'success': False, 'error': str(e), 'recommendations': {}}

    def _format_products(self, products):
        result = []
        for product in products:
            try:
                combination_info = product.product_tmpl_id._get_combination_info(
                    combination=product.product_template_attribute_value_ids,
                    product_id=product.id,
                    add_qty=1,
                )
                discount_pct = 0
                if combination_info.get('compare_list_price') and combination_info.get('price'):
                    if combination_info['compare_list_price'] > combination_info['price']:
                        discount_pct = round(
                            (1 - combination_info['price'] / combination_info['compare_list_price']) * 100
                        )
                result.append({
                    'id': product.id,
                    'name': product.name,
                    'display_name': product.display_name,
                    'image_url': f'/web/image/product.product/{product.id}/image_512',
                    'url': f'/shop/product/{product.product_tmpl_id.id}',
                    'price': combination_info.get('price', 0),
                    'list_price': combination_info.get('list_price', 0),
                    'compare_list_price': combination_info.get('compare_list_price', 0),
                    'currency_symbol': request.website.currency_id.symbol,
                    'currency_position': request.website.currency_id.position,
                    'has_discount': discount_pct > 0,
                    'discount_pct': discount_pct,
                    'rating': product.rating_avg or 0,
                    'rating_count': product.rating_count or 0,
                    'in_stock': product.is_storable and product.free_qty > 0 or not product.is_storable,
                })
            except Exception as e:
                _logger.warning(f"Erreur formatage produit {product.id}: {e}")
                continue
        return result

    # -------------------------------------------------------------------------
    # NOUVELLE ROUTE — fallback catégories principales (sans restriction website)
    # -------------------------------------------------------------------------
    @http.route('/shop/main_categories', type='jsonrpc', auth='public', website=True)
    def get_main_categories(self, limit=6):
        """
        Retourne les catégories racines du shop pour le site courant.
        Utilisé comme fallback par le widget PreferredCategories.
        Route publique, sans restriction de website.
        """
        try:
            categories = request.env['product.public.category'].sudo().search([
                ('website_id', 'in', [request.website.id, False]),
                ('parent_id', '=', False),
            ], limit=int(limit))
            result = [{
                'id': cat.id,
                'name': cat.name,
                'image_url': f'/web/image/product.public.category/{cat.id}/image_512',
            } for cat in categories]
            return {'success': True, 'categories': result}
        except Exception as e:
            _logger.error(f"Erreur récupération catégories principales: {e}")
            return {'success': False, 'categories': []}

    @http.route('/shop/preferences/categories', type='jsonrpc', auth='public', website=True)
    def get_preferred_categories(self, limit=5):
        if not self._is_lolirine_pool_website():
            return {'success': False, 'error': 'Not on Lolirine Pool website', 'categories': []}
        try:
            visitor_info = self._get_visitor_info()
            Preference = request.env['visitor.category.preference'].sudo()
            domain = []
            if visitor_info['partner_id']:
                domain.append(('partner_id', '=', visitor_info['partner_id']))
            elif visitor_info['visitor_id']:
                domain.append(('visitor_id', '=', visitor_info['visitor_id']))
            else:
                return {'success': True, 'categories': []}
            preferences = Preference.search(domain, order='score desc', limit=limit)
            categories = [{
                'id': pref.category_id.id,
                'name': pref.category_id.name,
                'score': pref.score,
                'image_url': f'/web/image/product.public.category/{pref.category_id.id}/image_512',
            } for pref in preferences]
            return {'success': True, 'categories': categories}
        except Exception as e:
            _logger.error(f"Erreur récupération catégories préférées: {e}")
            return {'success': False, 'error': str(e), 'categories': []}
