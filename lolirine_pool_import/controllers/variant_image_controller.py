# -*- coding: utf-8 -*-
"""
Contrôleur HTTP pour les images variantes.
Fournit :
  - /pool/variant_images/<tmpl_id>  → JSON de toutes les PTAV avec images
  - /pool/variant_image/<ptav_id>   → image binaire d'une PTAV
  - /pool/variant_images/assign     → endpoint batch (admin)
"""

from odoo import http
from odoo.http import request, content_disposition
import base64
import json
import logging

_logger = logging.getLogger(__name__)


class VariantImageController(http.Controller):

    @http.route('/pool/variant_images/<int:tmpl_id>', type='json',
                auth='public', website=True, methods=['POST'])
    def get_variant_images_json(self, tmpl_id, **kwargs):
        """
        Retourne un dict des images variantes pour un product.template.
        Appelé par le JS frontend pour pré-charger les images.

        Response :
        {
          "attribute_values": {
            "<ptav_id>": {
              "attribute_id": 42,
              "attribute_name": "Meuble",
              "value_name": "BUTTERFLY",
              "image_url": "/pool/variant_image/123",
              "has_image": true
            },
            ...
          },
          "default_image_url": "/web/image/product.template/99/image_1920"
        }
        """
        template = request.env['product.template'].sudo().browse(tmpl_id)
        if not template.exists():
            return {'error': 'Product not found'}

        result = {
            'attribute_values': {},
            'default_image_url': f'/web/image/product.template/{tmpl_id}/image_1920',
        }

        for line in template.attribute_line_ids:
            for ptav in line.product_template_value_ids:
                has_image = bool(ptav.variant_image)
                result['attribute_values'][str(ptav.id)] = {
                    'attribute_id': line.attribute_id.id,
                    'attribute_name': line.attribute_id.name,
                    'value_id': ptav.product_attribute_value_id.id,
                    'value_name': ptav.product_attribute_value_id.name,
                    'image_url': f'/pool/variant_image/{ptav.id}' if has_image else '',
                    'image_url_external': ptav.variant_image_url or '',
                    'has_image': has_image,
                }

        return result

    @http.route('/pool/variant_image/<int:ptav_id>', type='http',
                auth='public', website=True, sitemap=False)
    def get_variant_image(self, ptav_id, **kwargs):
        """Sert l'image binaire d'une PTAV (1920px)."""
        ptav = request.env['product.template.attribute.value'].sudo().browse(ptav_id)
        if not ptav.exists() or not ptav.variant_image:
            return request.not_found()

        image_data = base64.b64decode(ptav.variant_image)

        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Length', len(image_data)),
            ('Cache-Control', 'public, max-age=604800'),  # 7j de cache
        ]
        return request.make_response(image_data, headers)

    @http.route('/pool/variant_image_128/<int:ptav_id>', type='http',
                auth='public', website=True, sitemap=False)
    def get_variant_image_thumb(self, ptav_id, **kwargs):
        """Miniature 128px pour les sélecteurs visuels."""
        ptav = request.env['product.template.attribute.value'].sudo().browse(ptav_id)
        if not ptav.exists() or not ptav.variant_image_128:
            return request.not_found()

        image_data = base64.b64decode(ptav.variant_image_128)
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Length', len(image_data)),
            ('Cache-Control', 'public, max-age=604800'),
        ]
        return request.make_response(image_data, headers)

    @http.route('/pool/variant_images/batch_assign', type='json',
                auth='user', methods=['POST'])
    def batch_assign_variant_images(self, domain=None, **kwargs):
        """
        Endpoint admin pour lancer le batch d'assignation.
        Appelable depuis un bouton backend ou un script.
        """
        ProductTemplate = request.env['product.template']
        if domain:
            templates = ProductTemplate.search(domain)
        else:
            templates = None

        result = ProductTemplate._batch_assign_variant_images(templates)
        return result
