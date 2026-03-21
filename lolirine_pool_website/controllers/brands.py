# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class BrandsController(http.Controller):

    @http.route('/marques', type='http', auth='public', website=True)
    def brands_page(self, **kwargs):
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
                    'product_count': count,
                })

        return request.render('lolirine_pool_website.brands_page', {
            'brands': brands_data,
        })


class WebsiteSaleBrands(WebsiteSale):

    @http.route('/shop/marque/<int:brand_id>', type='http', auth='public', website=True)
    def shop_by_brand(self, brand_id, page=0, **kwargs):
        brand = request.env['pool.brand'].sudo().browse(brand_id)
        if not brand.exists():
            return request.redirect('/marques')

        domain = [
            ('pool_brand_id', '=', brand_id),
            ('website_id', '=', request.website.id),
            ('is_published', '=', True),
        ]

        Product = request.env['product.template'].sudo()
        products = Product.search(domain, limit=20, offset=page * 20)
        product_count = Product.search_count(domain)

        pager = request.website.pager(
            url=f'/shop/marque/{brand_id}',
            total=product_count,
            page=page,
            step=20,
        )

        return request.render('lolirine_pool_website.shop_brand_page', {
            'brand': brand,
            'products': products,
            'product_count': product_count,
            'pager': pager,
        })
