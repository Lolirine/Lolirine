# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Website(models.Model):
    _inherit = 'website'
    
    is_pool_website = fields.Boolean(
        string='Site Piscine',
        default=False,
        help="Cochez pour identifier ce site comme le site Pool Store"
    )
    
    # Routes standard d'Odoo (ou de modules garde-meuble) sans interet pour le
    # Pool Store : retirees de son sitemap. Les pages restent accessibles.
    SITEMAP_EXCLUS_POOL = {
        '/contact', '/contactus', '/terms', '/website/info',
        '/appointment', '/calendar', '/blog', '/forum',
    }
    SITEMAP_PREFIXES_EXCLUS_POOL = (
        '/appointment/', '/calendar/', '/blog/', '/forum/', '/profile/', '/sign/',
    )

    def _sitemap_exclu_pool(self, loc):
        loc = (loc or '').split('?')[0]
        return loc in self.SITEMAP_EXCLUS_POOL or loc.startswith(self.SITEMAP_PREFIXES_EXCLUS_POOL)

    def _enumerate_pages(self, query_string=None, force=False):
        pages = super()._enumerate_pages(query_string=query_string, force=force)
        if not (self.id == 6 or self.is_pool_website):
            yield from pages
            return
        vus = set()
        for page in pages:
            loc = page.get('loc', '')
            if loc in vus or self._sitemap_exclu_pool(loc):
                continue
            vus.add(loc)
            yield page

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
