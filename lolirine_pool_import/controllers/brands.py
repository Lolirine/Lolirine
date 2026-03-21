# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class BrandsController(http.Controller):

    @http.route('/marques', type='http', auth='public', website=True)
    def brands_page(self, **kwargs):
        """Page de navigation par marque."""
        brands = request.env['pool.brand'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')

        brands_data = []
        for brand in brands:
            count = request.env['product.template'].sudo().search_count([
                ('pool_brand_id', '=', brand.id),
                ('website_id', '=', request.website.id),
                ('is_published', '=', True),
            ])
            if count > 0:
                brands_data.append({
                    'id': brand.id,
                    'name': brand.name,
                    'logo': brand.logo,
                    'description': brand.description or '',
                    'website_url': brand.website_url or '',
                    'product_count': count,
                })

        return request.render('lolirine_pool_website.brands_page', {
            'brands': brands_data,
        })
