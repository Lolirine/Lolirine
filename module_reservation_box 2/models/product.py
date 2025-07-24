from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_disponible = fields.Boolean(string='Disponible pour réservation', default=False)