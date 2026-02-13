# -*- coding: utf-8 -*-
"""
Filtre les attributs du shop par catégorie ET par website.
- Dans une catégorie : seuls les attributs des produits de cette catégorie
- Sans catégorie : seuls les attributs des produits publiés sur CE website
"""

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import http
from odoo.http import request


class WebsiteSaleCategoryFilter(WebsiteSale):

    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        response = super().shop(
            page=page, category=category, search=search,
            min_price=min_price, max_price=max_price, ppg=ppg, **post
        )

        if hasattr(response, 'qcontext') and 'attributes' in response.qcontext:
            try:
                cat_obj = response.qcontext.get('category')
                cat_id = cat_obj.id if cat_obj and hasattr(cat_obj, 'id') else 0
                self._filter_attributes_for_context(response, cat_id)
            except Exception:
                pass  # En cas d'erreur, on laisse les filtres par défaut

        return response

    def _filter_attributes_for_context(self, response, category_id):
        """Filtre les attributs selon la catégorie et le website courant."""
        # Domaine de base : produits publiés sur ce website
        base_domain = request.website.sale_product_domain()

        if category_id:
            # Sous-catégories incluses
            child_cats = request.env['product.public.category'].sudo().search([
                ('id', 'child_of', [category_id])
            ])
            base_domain += [('public_categ_ids', 'in', child_cats.ids)]

        products = request.env['product.template'].sudo().search(base_domain)

        if not products:
            response.qcontext['attributes'] = response.qcontext['attributes'].browse([])
            return

        # Attributs réellement utilisés par ces produits
        used_attribute_ids = products.mapped(
            'attribute_line_ids.attribute_id'
        ).ids

        if not used_attribute_ids:
            response.qcontext['attributes'] = response.qcontext['attributes'].browse([])
            return

        # Ne garder que les attributs pertinents
        original_attrs = response.qcontext['attributes']
        response.qcontext['attributes'] = original_attrs.filtered(
            lambda a: a.id in used_attribute_ids
        )
