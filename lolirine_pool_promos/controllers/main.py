from odoo import http
from odoo.http import request


class PoolPromotionController(http.Controller):

    @http.route('/shop/promotions', type='http', auth='public', website=True, sitemap=True)
    def promotions_page(self, **kwargs):
        today = request.env['pool.promotion']._fields['date_start'].today()
        domain = [
            ('active', '=', True),
            ('date_start', '<=', today),
            ('date_end', '>=', today),
        ]
        website = request.website
        if website:
            domain += [
                '|',
                ('website_id', '=', False),
                ('website_id', '=', website.id),
            ]
            # Only accessible on Pool Store
            pool_store_id = int(request.env['ir.config_parameter'].sudo().get_param(
                'lolirine_pool_promos.website_id', '6'))
            if pool_store_id and website.id != pool_store_id:
                return request.redirect('/')
        promotions = request.env['pool.promotion'].sudo().search(domain, order='sequence, id')
        return request.render('lolirine_pool_promos.promotions_page_template', {
            'promotions': promotions,
        })
