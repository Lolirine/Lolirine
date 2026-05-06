# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64


class VariantImageController(http.Controller):

    @http.route('/pool/variant_images/<int:tmpl_id>', type='jsonrpc',
                auth='public', website=True, methods=['POST'])
    def get_variant_images_json(self, tmpl_id, **kwargs):
        template = request.env['product.template'].sudo().browse(tmpl_id)
        if not template.exists():
            return {'error': 'Product not found'}

        result = {
            'attribute_values': {},
            'default_image_url': '/web/image/product.template/%d/image_1920' % tmpl_id,
        }
        for line in template.attribute_line_ids:
            for ptav in line.product_template_value_ids:
                has_image = bool(ptav.variant_image)
                result['attribute_values'][str(ptav.id)] = {
                    'attribute_id': line.attribute_id.id,
                    'attribute_name': line.attribute_id.name,
                    'value_name': ptav.product_attribute_value_id.name,
                    'image_url': '/pool/variant_image/%d' % ptav.id if has_image else '',
                    'has_image': has_image,
                }
        return result

    @http.route('/pool/variant_image/<int:ptav_id>', type='http',
                auth='public', website=True, sitemap=False)
    def get_variant_image(self, ptav_id, **kwargs):
        ptav = request.env['product.template.attribute.value'].sudo().browse(ptav_id)
        if not ptav.exists() or not ptav.variant_image:
            return request.not_found()
        image_data = base64.b64decode(ptav.variant_image)
        return request.make_response(image_data, [
            ('Content-Type', 'image/png'),
            ('Content-Length', len(image_data)),
            ('Cache-Control', 'public, max-age=604800'),
        ])

    @http.route('/pool/variant_image_128/<int:ptav_id>', type='http',
                auth='public', website=True, sitemap=False)
    def get_variant_image_thumb(self, ptav_id, **kwargs):
        ptav = request.env['product.template.attribute.value'].sudo().browse(ptav_id)
        if not ptav.exists() or not ptav.variant_image_128:
            return request.not_found()
        image_data = base64.b64decode(ptav.variant_image_128)
        return request.make_response(image_data, [
            ('Content-Type', 'image/png'),
            ('Content-Length', len(image_data)),
            ('Cache-Control', 'public, max-age=604800'),
        ])
