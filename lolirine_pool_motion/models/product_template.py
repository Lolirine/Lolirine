# models/product_template.py
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_pool_suggested_ids = fields.Many2many(
        "product.template",
        relation="product_template_pool_suggested_rel",
        column1="src_tmpl_id",
        column2="dest_tmpl_id",
        string="Complétez votre équipement",
        help="Produits complémentaires suggérés sous les produits alternatifs.",
    )
