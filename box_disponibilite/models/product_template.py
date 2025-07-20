from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    disponible_a_la_location = fields.Boolean(string="Disponible à la location", default=True)
