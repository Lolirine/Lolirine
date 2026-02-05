import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VariantImageWizard(models.TransientModel):
    _name = 'variant.image.wizard'
    _description = "Wizard de gestion des images par variante"

    product_tmpl_id = fields.Many2one(
        'product.template',
        string="Produit",
        required=True,
    )
    line_ids = fields.One2many(
        'variant.image.wizard.line',
        'wizard_id',
        string="Variantes",
    )
    variant_count = fields.Integer(
        compute='_compute_variant_count',
    )

    @api.depends('line_ids')
    def _compute_variant_count(self):
        for wiz in self:
            wiz.variant_count = len(wiz.line_ids)

    def action_apply(self):
        """Applique les images aux variantes."""
        self.ensure_one()
        updated = 0
        for line in self.line_ids:
            if line.new_image and line.new_image != (line.variant_id.image_1920 or False):
                line.variant_id.write({'image_1920': line.new_image})
                updated += 1
            elif line.clear_image and line.variant_id.image_1920:
                line.variant_id.write({'image_1920': False})
                updated += 1
        _logger.info("Images mises à jour pour %d variantes de %s", updated, self.product_tmpl_id.name)
        return {'type': 'ir.actions.act_window_close'}

    def action_copy_first_to_all(self):
        """Copie l'image de la première variante vers toutes les autres sans image."""
        self.ensure_one()
        first_with_image = self.line_ids.filtered(lambda l: l.new_image or l.current_image)
        if first_with_image:
            source_image = first_with_image[0].new_image or first_with_image[0].variant_id.image_1920
            if source_image:
                for line in self.line_ids:
                    if not line.new_image and not line.current_image:
                        line.new_image = source_image


class VariantImageWizardLine(models.TransientModel):
    _name = 'variant.image.wizard.line'
    _description = 'Ligne du wizard images variantes'

    wizard_id = fields.Many2one(
        'variant.image.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade',
    )
    variant_id = fields.Many2one(
        'product.product',
        string="Variante",
        required=True,
    )
    variant_name = fields.Char(
        string="Combinaison",
        readonly=True,
    )
    attribute_values = fields.Char(
        string="Attributs",
        readonly=True,
    )
    current_image = fields.Html(
        string="Image actuelle",
        compute='_compute_current_image',
        sanitize=False,
    )
    new_image = fields.Binary(
        string="Nouvelle image",
    )
    clear_image = fields.Boolean(
        string="Supprimer",
        default=False,
    )
    has_image = fields.Boolean(
        compute='_compute_has_image',
    )

    @api.depends('variant_id')
    def _compute_current_image(self):
        for line in self:
            if line.variant_id.image_1920:
                line.current_image = (
                    '<img src="/web/image/product.product/%d/image_128" '
                    'style="width:64px;height:64px;object-fit:contain;'
                    'border-radius:6px;border:1px solid #ddd;" />'
                    % line.variant_id.id
                )
            else:
                line.current_image = (
                    '<span style="display:inline-block;width:64px;height:64px;'
                    'background:#f8f9fa;border-radius:6px;'
                    'border:2px dashed #ccc;text-align:center;'
                    'line-height:64px;color:#aaa;font-size:12px;">'
                    'Aucune</span>'
                )

    @api.depends('variant_id')
    def _compute_has_image(self):
        for line in self:
            line.has_image = bool(line.variant_id.image_1920)
