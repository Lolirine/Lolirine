from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_specs_techniques = fields.Html(
        string="Caractéristiques techniques",
        translate=True,
        sanitize=False,
    )
