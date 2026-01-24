# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class PoolCategoriesController(http.Controller):
    """
    Controller pour les pages Boutique et Univers avec liens dynamiques
    vers les catégories e-commerce.
    """

    def _get_category_by_xmlid(self, xmlid):
        """Récupère une catégorie par son XML ID"""
        try:
            return request.env.ref(xmlid, raise_if_not_found=False)
        except Exception:
            return None

    def _get_category_url(self, category):
        """Génère l'URL d'une catégorie produit"""
        if category:
            # Format: /shop/category/slug-id
            slug = category.name.lower().replace(' ', '-').replace('&', '').replace('  ', '-')
            return f'/shop/category/{slug}-{category.id}'
        return '/shop'

    def _get_universes_data(self):
        """Récupère les données des 4 univers principaux"""
        module = 'lolirine_pool_categories'
        
        universes = [
            {
                'name': 'Traitement de l\'eau',
                'icon': 'fa-tint',
                'color': 'cyan',
                'gradient': 'linear-gradient(135deg, #0891b2 0%, #0e7490 100%)',
                'page_url': '/boutique/traitement-eau',
                'xmlid': f'{module}.categ_traitement_eau',
            },
            {
                'name': 'Nettoyage & Robots',
                'icon': 'fa-robot',
                'color': 'gray',
                'gradient': 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
                'page_url': '/boutique/nettoyage-robots',
                'xmlid': f'{module}.categ_nettoyage',
            },
            {
                'name': 'Espace Wellness',
                'icon': 'fa-hot-tub',
                'color': 'orange',
                'gradient': 'linear-gradient(135deg, #d97706 0%, #b45309 100%)',
                'page_url': '/boutique/wellness',
                'xmlid': f'{module}.categ_wellness',
            },
            {
                'name': 'Équipements & Pièces',
                'icon': 'fa-cogs',
                'color': 'teal',
                'gradient': 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
                'page_url': '/boutique/equipements',
                'xmlid': f'{module}.categ_equipements',
            },
        ]
        
        # Ajouter les URLs dynamiques
        for universe in universes:
            category = self._get_category_by_xmlid(universe['xmlid'])
            universe['category'] = category
            universe['shop_url'] = self._get_category_url(category)
        
        return universes

    def _get_subcategories(self, parent_xmlid):
        """Récupère les sous-catégories d'un univers"""
        parent = self._get_category_by_xmlid(parent_xmlid)
        if not parent:
            return []
        
        subcategories = request.env['product.public.category'].sudo().search([
            ('parent_id', '=', parent.id)
        ], order='sequence')
        
        result = []
        for cat in subcategories:
            result.append({
                'id': cat.id,
                'name': cat.name,
                'description': cat.website_description or '',
                'url': self._get_category_url(cat),
                'image': cat.image_1920 if hasattr(cat, 'image_1920') else None,
            })
        
        return result

    # =============================================
    # ROUTES
    # =============================================

    @http.route('/boutique', type='http', auth='public', website=True)
    def page_boutique(self, **kwargs):
        """Page principale Boutique avec les 4 univers"""
        values = {
            'universes': self._get_universes_data(),
        }
        return request.render('lolirine_pool_categories.page_boutique_dynamic', values)

    @http.route('/boutique/traitement-eau', type='http', auth='public', website=True)
    def page_traitement_eau(self, **kwargs):
        """Page univers Traitement de l'eau"""
        module = 'lolirine_pool_categories'
        parent_xmlid = f'{module}.categ_traitement_eau'
        parent = self._get_category_by_xmlid(parent_xmlid)
        
        # Icônes pour chaque sous-catégorie
        icons = {
            'Chlore & Brome': 'fa-vial',
            'pH & Alcalinité': 'fa-balance-scale',
            'Anti-algues': 'fa-leaf',
            'Traitement choc': 'fa-bolt',
            'Produits hivernage': 'fa-snowflake',
            'Analyse & Tests': 'fa-flask',
            'Électrolyse au sel': 'fa-microchip',
        }
        
        subcategories = self._get_subcategories(parent_xmlid)
        for sub in subcategories:
            sub['icon'] = icons.get(sub['name'], 'fa-box')
        
        values = {
            'universe_name': 'Traitement de l\'eau',
            'parent_url': self._get_category_url(parent),
            'subcategories': subcategories,
        }
        return request.render('lolirine_pool_categories.page_traitement_eau', values)

    @http.route('/boutique/nettoyage-robots', type='http', auth='public', website=True)
    def page_nettoyage(self, **kwargs):
        """Page univers Nettoyage & Robots"""
        module = 'lolirine_pool_categories'
        parent_xmlid = f'{module}.categ_nettoyage'
        parent = self._get_category_by_xmlid(parent_xmlid)
        
        icons = {
            'Robots automatiques': 'fa-robot',
            'Aspirateurs & Balais': 'fa-broom',
            'Épuisettes & Brosses': 'fa-hand-sparkles',
            'Manches & Tuyaux': 'fa-grip-lines',
            'Accessoires nettoyage': 'fa-tools',
        }
        
        subcategories = self._get_subcategories(parent_xmlid)
        for sub in subcategories:
            sub['icon'] = icons.get(sub['name'], 'fa-box')
        
        values = {
            'universe_name': 'Nettoyage & Robots',
            'parent_url': self._get_category_url(parent),
            'subcategories': subcategories,
        }
        return request.render('lolirine_pool_categories.page_nettoyage_robots', values)

    @http.route('/boutique/wellness', type='http', auth='public', website=True)
    def page_wellness(self, **kwargs):
        """Page univers Espace Wellness"""
        module = 'lolirine_pool_categories'
        parent_xmlid = f'{module}.categ_wellness'
        parent = self._get_category_by_xmlid(parent_xmlid)
        
        icons = {
            'Spas & Jacuzzis': 'fa-hot-tub',
            'Spas gonflables': 'fa-wind',
            'Saunas': 'fa-fire',
            'Accessoires spa': 'fa-couch',
            'Traitement spa': 'fa-flask',
        }
        
        subcategories = self._get_subcategories(parent_xmlid)
        for sub in subcategories:
            sub['icon'] = icons.get(sub['name'], 'fa-box')
        
        values = {
            'universe_name': 'Espace Wellness',
            'parent_url': self._get_category_url(parent),
            'subcategories': subcategories,
        }
        return request.render('lolirine_pool_categories.page_wellness', values)

    @http.route('/boutique/equipements', type='http', auth='public', website=True)
    def page_equipements(self, **kwargs):
        """Page univers Équipements & Pièces"""
        module = 'lolirine_pool_categories'
        parent_xmlid = f'{module}.categ_equipements'
        parent = self._get_category_by_xmlid(parent_xmlid)
        
        icons = {
            'Pompes': 'fa-sync-alt',
            'Filtres & Média filtrant': 'fa-filter',
            'Chauffage & PAC': 'fa-thermometer-half',
            'Éclairage LED': 'fa-lightbulb',
            'Liners & Revêtements': 'fa-layer-group',
            'Échelles & Plongeoirs': 'fa-arrow-up',
            'Bâches & Couvertures': 'fa-shield-alt',
            'Skimmers & Buses': 'fa-water',
            'Pièces détachées': 'fa-puzzle-piece',
        }
        
        subcategories = self._get_subcategories(parent_xmlid)
        for sub in subcategories:
            sub['icon'] = icons.get(sub['name'], 'fa-box')
        
        values = {
            'universe_name': 'Équipements & Pièces',
            'parent_url': self._get_category_url(parent),
            'subcategories': subcategories,
        }
        return request.render('lolirine_pool_categories.page_equipements_pieces', values)
