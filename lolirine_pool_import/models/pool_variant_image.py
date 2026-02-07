# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplateAttributeValueImage(models.Model):
    _inherit = 'product.template.attribute.value'

    variant_image = fields.Image(
        string='Image variante',
        max_width=1920, max_height=1920,
    )
    variant_image_128 = fields.Image(
        string='Miniature',
        related='variant_image',
        max_width=128, max_height=128,
        store=True,
    )


class ProductTemplateVariantImages(models.Model):
    _inherit = 'product.template'

    variant_images_configured = fields.Boolean(
        string='Images variantes configurées',
        default=False,
        copy=False,
    )
