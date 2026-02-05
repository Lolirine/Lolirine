from odoo import api, fields, models


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    visual_preview = fields.Html(
        string="Aperçu visuel",
        compute='_compute_visual_preview',
        sanitize=False,
    )

    @api.depends('image', 'html_color', 'attribute_id.display_type')
    def _compute_visual_preview(self):
        for val in self:
            if val.image:
                val.visual_preview = (
                    '<img src="/web/image/product.attribute.value/%d/image" '
                    'style="width:40px;height:40px;object-fit:cover;border-radius:4px;'
                    'border:1px solid #ddd;" />' % val.id
                )
            elif val.html_color:
                val.visual_preview = (
                    '<span style="display:inline-block;width:40px;height:40px;'
                    'background-color:%s;border-radius:4px;border:1px solid #ddd;">'
                    '</span>' % val.html_color
                )
            else:
                val.visual_preview = (
                    '<span style="display:inline-block;width:40px;height:40px;'
                    'background:#f0f0f0;border-radius:4px;border:1px dashed #ccc;'
                    'text-align:center;line-height:40px;font-size:18px;color:#aaa;">'
                    '?</span>'
                )


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
