# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class PoolWebsiteSale(WebsiteSale):
    """Extension du controller e-commerce pour le site piscine"""
    
    @http.route(['/shop/pool'], type='http', auth='public', website=True)
    def pool_shop(self, **kwargs):
        """Page d'accueil du shop piscine"""
        # Catégories principales piscine
        PoolCategory = request.env['pool.product.category']
        categories = PoolCategory.sudo().search([
            ('parent_id', '=', False),
            ('active', '=', True)
        ], order='sequence')
        
        # Marques populaires
        brands = request.env['pool.brand'].sudo().search([
            ('active', '=', True)
        ], limit=10)
        
        # Produits en vedette
        featured_products = request.env['product.template'].sudo().search([
            ('is_pool_product', '=', True),
            ('website_published', '=', True),
        ], limit=8, order='create_date desc')
        
        values = {
            'categories': categories,
            'brands': brands,
            'featured_products': featured_products,
        }
        
        return request.render('lolirine_pool.pool_shop_home', values)
    
    @http.route(['/shop/pool/category/<model("pool.product.category"):category>'],
                type='http', auth='public', website=True)
    def pool_category(self, category, **kwargs):
        """Page catégorie piscine"""
        # Produits de la catégorie
        domain = [
            ('is_pool_product', '=', True),
            ('website_published', '=', True),
        ]
        
        if category.product_category_id:
            domain.append(('categ_id', 'child_of', category.product_category_id.id))
        
        products = request.env['product.template'].sudo().search(domain, limit=50)
        
        # Sous-catégories
        subcategories = request.env['pool.product.category'].sudo().search([
            ('parent_id', '=', category.id),
            ('active', '=', True)
        ])
        
        values = {
            'category': category,
            'subcategories': subcategories,
            'products': products,
        }
        
        return request.render('lolirine_pool.pool_category_page', values)
    
    @http.route(['/shop/pool/brand/<model("pool.brand"):brand>'],
                type='http', auth='public', website=True)
    def pool_brand(self, brand, **kwargs):
        """Page marque"""
        products = request.env['product.template'].sudo().search([
            ('is_pool_product', '=', True),
            ('website_published', '=', True),
            ('pool_brand_id', '=', brand.id),
        ], limit=50)
        
        values = {
            'brand': brand,
            'products': products,
        }
        
        return request.render('lolirine_pool.pool_brand_page', values)
    
    @http.route(['/shop/pool/search'], type='http', auth='public', website=True)
    def pool_search(self, search='', **kwargs):
        """Recherche produits piscine"""
        domain = [
            ('is_pool_product', '=', True),
            ('website_published', '=', True),
            '|', '|', '|',
            ('name', 'ilike', search),
            ('default_code', 'ilike', search),
            ('description_sale', 'ilike', search),
            ('pool_brand', 'ilike', search),
        ]
        
        products = request.env['product.template'].sudo().search(domain, limit=50)
        
        values = {
            'search': search,
            'products': products,
            'search_count': len(products),
        }
        
        return request.render('lolirine_pool.pool_search_results', values)
    
    @http.route(['/shop/pool/configurator'], type='http', auth='public', website=True)
    def pool_configurator(self, **kwargs):
        """Configurateur de piscine (futur)"""
        values = {}
        return request.render('lolirine_pool.pool_configurator', values)


class PoolAPI(http.Controller):
    """API REST pour intégrations"""
    
    @http.route(['/api/pool/products'], type='json', auth='user', methods=['GET'])
    def get_products(self, category_id=None, brand_id=None, limit=100, offset=0):
        """Récupérer les produits piscine"""
        domain = [('is_pool_product', '=', True)]
        
        if category_id:
            domain.append(('pool_category_id', '=', int(category_id)))
        if brand_id:
            domain.append(('pool_brand_id', '=', int(brand_id)))
        
        products = request.env['product.template'].search(
            domain, limit=limit, offset=offset
        )
        
        return [{
            'id': p.id,
            'name': p.name,
            'ref': p.default_code,
            'price': p.list_price,
            'brand': p.pool_brand,
            'category': p.pool_category_id.name if p.pool_category_id else None,
        } for p in products]
    
    @http.route(['/api/pool/stock/<int:product_id>'], type='json', auth='user', methods=['GET'])
    def get_stock(self, product_id):
        """Récupérer le stock d'un produit"""
        product = request.env['product.product'].browse(product_id)
        if not product.exists():
            return {'error': 'Product not found'}
        
        return {
            'id': product.id,
            'name': product.name,
            'qty_available': product.qty_available,
            'virtual_available': product.virtual_available,
            'supplier_stock': product.product_tmpl_id.supplier_stock_qty,
        }
