# -*- coding: utf-8 -*-

from odoo import models, api


class Website(models.Model):
    _inherit = 'website'

    def _get_pool_category_by_xmlid(self, xmlid):
        """Récupère une catégorie par son XML ID"""
        try:
            return self.env.ref(xmlid, raise_if_not_found=False)
        except Exception:
            return None

    def _get_pool_category_url(self, category):
        """Génère l'URL d'une catégorie produit"""
        if category:
            slug = category.name.lower().replace(' ', '-').replace('&', '').replace('  ', '-')
            return f'/shop/category/{slug}-{category.id}'
        return '/shop'

    def get_pool_subcategories(self, universe_key):
        """
        Récupère les sous-catégories d'un univers
        universe_key: 'traitement_eau', 'nettoyage', 'wellness', 'equipements'
        """
        module = 'lolirine_pool_categories'
        
        universe_config = {
            'traitement_eau': {
                'xmlid': f'{module}.categ_traitement_eau',
                'icons': {
                    'Chlore & Brome': 'fa-vial',
                    'pH & Alcalinité': 'fa-balance-scale',
                    'Anti-algues': 'fa-leaf',
                    'Traitement choc': 'fa-bolt',
                    'Produits hivernage': 'fa-snowflake',
                    'Analyse & Tests': 'fa-flask',
                    'Électrolyse au sel': 'fa-microchip',
                },
            },
            'nettoyage': {
                'xmlid': f'{module}.categ_nettoyage',
                'icons': {
                    'Robots automatiques': 'fa-robot',
                    'Aspirateurs & Balais': 'fa-broom',
                    'Épuisettes & Brosses': 'fa-hand-sparkles',
                    'Manches & Tuyaux': 'fa-grip-lines',
                    'Accessoires nettoyage': 'fa-tools',
                },
            },
            'wellness': {
                'xmlid': f'{module}.categ_wellness',
                'icons': {
                    'Spas & Jacuzzis': 'fa-hot-tub',
                    'Spas gonflables': 'fa-wind',
                    'Saunas': 'fa-fire',
                    'Accessoires spa': 'fa-couch',
                    'Traitement spa': 'fa-flask',
                },
            },
            'equipements': {
                'xmlid': f'{module}.categ_equipements',
                'icons': {
                    'Pompes': 'fa-sync-alt',
                    'Filtres & Média filtrant': 'fa-filter',
                    'Chauffage & PAC': 'fa-thermometer-half',
                    'Éclairage LED': 'fa-lightbulb',
                    'Liners & Revêtements': 'fa-layer-group',
                    'Échelles & Plongeoirs': 'fa-arrow-up',
                    'Bâches & Couvertures': 'fa-shield-alt',
                    'Skimmers & Buses': 'fa-water',
                    'Pièces détachées': 'fa-puzzle-piece',
                },
            },
        }
        
        config = universe_config.get(universe_key)
        if not config:
            return {'parent_url': '/shop', 'subcategories': []}
        
        parent = self._get_pool_category_by_xmlid(config['xmlid'])
        if not parent:
            return {'parent_url': '/shop', 'subcategories': []}
        
        subcategories = self.env['product.public.category'].sudo().search([
            ('parent_id', '=', parent.id)
        ], order='sequence')
        
        result = []
        for cat in subcategories:
            result.append({
                'id': cat.id,
                'name': cat.name,
                'description': cat.website_description or '',
                'url': self._get_pool_category_url(cat),
                'image': cat.image_1920 if hasattr(cat, 'image_1920') else None,
                'icon': config['icons'].get(cat.name, 'fa-box'),
            })
        
        return {
            'parent_url': self._get_pool_category_url(parent),
            'subcategories': result,
        }
