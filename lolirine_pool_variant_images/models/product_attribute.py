from odoo import api, fields, models


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    is_visual_attribute = fields.Boolean(
        string="Attribut visuel",
        compute='_compute_is_visual_attribute',
        store=True,
    )

    @api.depends('display_type')
    def _compute_is_visual_attribute(self):
        for attr in self:
            attr.is_visual_attribute = attr.display_type in ('color', 'image')
