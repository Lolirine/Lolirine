# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_storage_box = fields.Boolean(
        string='Est un box de stockage',
        default=False,
        help="Cochez cette case si ce produit représente un box de stockage"
    )
