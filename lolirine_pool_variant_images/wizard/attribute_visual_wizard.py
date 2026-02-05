import base64
import io
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    _logger.warning("Pillow non installé - génération auto d'images désactivée")


class AttributeVisualWizard(models.TransientModel):
    _name = 'attribute.visual.wizard'
    _description = "Wizard de gestion des visuels d'attributs"

    attribute_line_id = fields.Many2one(
        'product.template.attribute.line',
        string="Ligne d'attribut",
        required=True,
        ondelete='cascade',
    )
    attribute_id = fields.Many2one(
        'product.attribute',
        string="Attribut",
        required=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string="Produit",
        required=True,
    )
    line_ids = fields.One2many(
        'attribute.visual.wizard.line',
        'wizard_id',
        string="Valeurs",
    )

    def action_apply(self):
        """Applique les modifications de visuels aux valeurs d'attribut."""
        self.ensure_one()
        for line in self.line_ids:
            vals = {}

            if line.html_color != (line.attribute_value_id.html_color or False):
                vals['html_color'] = line.html_color or False

            if line.image != (line.attribute_value_id.image or False):
                vals['image'] = line.image or False

            # Générer une image de couleur si demandé
            if line.generate_color_image and line.html_color and not line.image:
                generated = self._generate_color_swatch(line.html_color)
                if generated:
                    vals['image'] = generated

            if vals:
                line.attribute_value_id.write(vals)

        return {'type': 'ir.actions.act_window_close'}

    @staticmethod
    def _generate_color_swatch(hex_color, size=128):
        """Génère une image de couleur unie."""
        if not HAS_PIL:
            return False
        try:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) != 6:
                return False
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)

            img = Image.new('RGB', (size, size), (r, g, b))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue())
        except Exception as e:
            _logger.warning("Erreur génération image couleur: %s", e)
            return False


class AttributeVisualWizardLine(models.TransientModel):
    _name = 'attribute.visual.wizard.line'
    _description = 'Ligne du wizard de visuels'

    wizard_id = fields.Many2one(
        'attribute.visual.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade',
    )
    attribute_value_id = fields.Many2one(
        'product.attribute.value',
        string="Valeur",
        required=True,
    )
    name = fields.Char(
        string="Nom",
        readonly=True,
    )
    html_color = fields.Char(
        string="Couleur HTML",
    )
    image = fields.Binary(
        string="Image",
    )
    current_visual = fields.Html(
        string="Actuel",
        compute='_compute_current_visual',
        sanitize=False,
    )
    generate_color_image = fields.Boolean(
        string="Auto-générer",
        default=False,
    )

    @api.depends('image', 'html_color')
    def _compute_current_visual(self):
        for line in self:
            if line.attribute_value_id.image:
                line.current_visual = (
                    '<img src="/web/image/product.attribute.value/%d/image" '
                    'style="width:48px;height:48px;object-fit:cover;'
                    'border-radius:6px;border:2px solid #ddd;" />'
                    % line.attribute_value_id.id
                )
            elif line.attribute_value_id.html_color:
                line.current_visual = (
                    '<span style="display:inline-block;width:48px;height:48px;'
                    'background-color:%s;border-radius:6px;'
                    'border:2px solid #ddd;"></span>'
                    % line.attribute_value_id.html_color
                )
            else:
                line.current_visual = (
                    '<span style="display:inline-block;width:48px;height:48px;'
                    'background:#f8f9fa;border-radius:6px;'
                    'border:2px dashed #ccc;text-align:center;'
                    'line-height:48px;color:#aaa;">?</span>'
                )
