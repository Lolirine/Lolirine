import base64
from PIL import Image
import io

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AttributeVisualWizard(models.TransientModel):
    _name = 'attribute.visual.wizard'
    _description = 'Wizard de gestion des visuels d\'attributs'

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
    display_type = fields.Selection(
        related='attribute_id.display_type',
        string="Type d'affichage",
        readonly=False,
    )
    line_ids = fields.One2many(
        'attribute.visual.wizard.line',
        'wizard_id',
        string="Valeurs",
    )

    def action_apply(self):
        """Applique les modifications de visuels aux valeurs d'attribut."""
        self.ensure_one()
        
        # Mettre à jour le display_type de l'attribut si changé
        if self.display_type != self.attribute_id.display_type:
            self.attribute_id.write({'display_type': self.display_type})

        for line in self.line_ids:
            vals = {}
            
            # Mettre à jour la couleur HTML
            if line.html_color != (line.attribute_value_id.html_color or False):
                vals['html_color'] = line.html_color or False
            
            # Mettre à jour l'image
            if line.image != (line.attribute_value_id.image or False):
                vals['image'] = line.image or False
            
            # Générer une image de couleur si couleur définie mais pas d'image
            if line.generate_color_image and line.html_color and not line.image:
                vals['image'] = self._generate_color_swatch(line.html_color)
            
            if vals:
                line.attribute_value_id.write(vals)
        
        return {'type': 'ir.actions.act_window_close'}

    def action_set_display_image(self):
        """Passe l'attribut en mode image."""
        self.attribute_id.write({'display_type': 'image'})
        self.display_type = 'image'

    def action_set_display_color(self):
        """Passe l'attribut en mode couleur."""
        self.attribute_id.write({'display_type': 'color'})
        self.display_type = 'color'

    @staticmethod
    def _generate_color_swatch(hex_color, size=128):
        """Génère une image de couleur unie avec léger dégradé."""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            
            img = Image.new('RGB', (size, size), (r, g, b))
            
            # Ajouter un léger effet de texture
            pixels = img.load()
            for y in range(size):
                for x in range(size):
                    # Léger dégradé diagonal
                    factor = 1.0 - (x + y) / (size * 4)
                    pixels[x, y] = (
                        max(0, min(255, int(r * factor))),
                        max(0, min(255, int(g * factor))),
                        max(0, min(255, int(b * factor))),
                    )
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue())
        except Exception:
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
        help="Code couleur hexadécimal (ex: #FF0000 pour rouge)",
    )
    image = fields.Binary(
        string="Image",
        help="Image de la texture/visuel (recommandé: 128x128px minimum)",
    )
    current_visual = fields.Html(
        string="Actuel",
        compute='_compute_current_visual',
        sanitize=False,
    )
    generate_color_image = fields.Boolean(
        string="Générer image",
        default=False,
        help="Générer automatiquement une image à partir de la couleur HTML",
    )

    @api.depends('image', 'html_color')
    def _compute_current_visual(self):
        for line in self:
            if line.image:
                line.current_visual = (
                    '<div style="display:flex;align-items:center;gap:8px;">'
                    '<img src="/web/image/product.attribute.value/%d/image" '
                    'style="width:48px;height:48px;object-fit:cover;border-radius:6px;'
                    'border:2px solid #ddd;box-shadow:0 1px 3px rgba(0,0,0,0.1);" />'
                    '<span style="color:#28a745;font-weight:bold;">✓ Image</span>'
                    '</div>' % line.attribute_value_id.id
                )
            elif line.html_color:
                line.current_visual = (
                    '<div style="display:flex;align-items:center;gap:8px;">'
                    '<span style="display:inline-block;width:48px;height:48px;'
                    'background-color:%s;border-radius:6px;border:2px solid #ddd;'
                    'box-shadow:0 1px 3px rgba(0,0,0,0.1);"></span>'
                    '<span style="color:#007bff;">Couleur</span>'
                    '</div>' % line.html_color
                )
            else:
                line.current_visual = (
                    '<div style="display:flex;align-items:center;gap:8px;">'
                    '<span style="display:inline-block;width:48px;height:48px;'
                    'background:#f8f9fa;border-radius:6px;border:2px dashed #ccc;'
                    'text-align:center;line-height:48px;font-size:20px;color:#aaa;">'
                    '?</span>'
                    '<span style="color:#dc3545;">Non défini</span>'
                    '</div>'
                )
