# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Website(models.Model):
    _inherit = 'website'
    
    is_pool_website = fields.Boolean(
        string='Site Piscine',
        default=False,
        help="Cochez pour identifier ce site comme le site Pool Store"
    )
    
    def _get_pool_categories(self):
        """Retourne les catégories piscine publiées"""
        return self.env['pool.website.category'].search([
            ('website_published', '=', True),
            ('parent_id', '=', False),  # Catégories racines uniquement
        ], order='sequence, name')
    
    def _get_featured_pool_products(self, limit=8):
        """Retourne les produits piscine mis en avant"""
        return self.env['product.template'].search([
            ('is_pool_product', '=', True),
            ('is_published', '=', True),
            ('website_id', 'in', [False, self.id]),
        ], limit=limit, order='create_date desc')
