# -*- coding: utf-8 -*-
"""
Filtre les attributs du shop par catégorie.
Quand un client navigue dans une catégorie, seuls les attributs
réellement présents sur les produits de cette catégorie s'affichent.
"""

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import http
from odoo.http import request


class WebsiteSaleCategoryFilter(WebsiteSale):

    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        # Appeler le shop standard
        response = super().shop(
            page=page, category=category, search=search,
            min_price=min_price, max_price=max_price, ppg=ppg, **post
        )

        # Si on est dans une catégorie, filtrer les attributs
        if category and hasattr(response, 'qcontext'):
            cat_obj = response.qcontext.get('category')
            if cat_obj and hasattr(cat_obj, 'id') and cat_obj.id:
                try:
                    self._filter_attributes_by_category(response, cat_obj)
                except Exception:
                    pass  # En cas d'erreur, on laisse les filtres par défaut

        return response

    def _filter_attributes_by_category(self, response, category):
        """Remplace la liste d'attributs par ceux de la catégorie uniquement."""
        # Trouver tous les produits publiés dans cette catégorie et ses enfants
        cat_ids = category.ids
        child_cats = request.env['product.public.category'].sudo().search([
            ('id', 'child_of', cat_ids)
        ])
        all_cat_ids = child_cats.ids or cat_ids

        # Produits publiés de la catégorie
        base_domain = request.website.sale_product_domain()
        domain = base_domain + [('public_categ_ids', 'in', all_cat_ids)]
        products = request.env['product.template'].sudo().search(domain)

        if not products:
            return

        # Attributs réellement utilisés par ces produits
        used_attribute_ids = products.mapped(
            'attribute_line_ids.attribute_id'
        ).ids

        if not used_attribute_ids:
            return

        # Filtrer les attributs dans le qcontext
        if 'attributes' in response.qcontext:
            original_attrs = response.qcontext['attributes']
            filtered = original_attrs.filtered(
                lambda a: a.id in used_attribute_ids
            )
            response.qcontext['attributes'] = filtered
