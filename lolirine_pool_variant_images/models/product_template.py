from odoo import api, fields, models


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    display_type = fields.Selection(
        related='attribute_id.display_type',
        string="Type d'affichage",
        readonly=True,
    )
    is_visual = fields.Boolean(
        compute='_compute_is_visual',
        string="Visuel",
    )

    @api.depends('attribute_id.display_type')
    def _compute_is_visual(self):
        for line in self:
            line.is_visual = line.attribute_id.display_type in ('color', 'image')

    def action_manage_visuals(self):
        """Ouvre le wizard pour gérer les visuels des valeurs d'attribut."""
        self.ensure_one()
        wizard = self.env['attribute.visual.wizard'].create({
            'attribute_line_id': self.id,
            'attribute_id': self.attribute_id.id,
            'product_tmpl_id': self.product_tmpl_id.id,
        })
        # Créer les lignes du wizard pour chaque valeur
        for value in self.value_ids:
            self.env['attribute.visual.wizard.line'].create({
                'wizard_id': wizard.id,
                'attribute_value_id': value.id,
                'name': value.name,
                'html_color': value.html_color or False,
                'image': value.image or False,
            })
        return {
            'name': 'Gérer les visuels - %s' % self.attribute_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'attribute.visual.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    has_visual_attributes = fields.Boolean(
        compute='_compute_has_visual_attributes',
        string="A des attributs visuels",
    )

    @api.depends('attribute_line_ids.attribute_id.display_type')
    def _compute_has_visual_attributes(self):
        for tmpl in self:
            tmpl.has_visual_attributes = any(
                line.attribute_id.display_type in ('color', 'image')
                for line in tmpl.attribute_line_ids
            )

    def action_open_visual_manager(self):
        """Ouvre le premier attribut visuel pour édition rapide."""
        self.ensure_one()
        visual_line = self.attribute_line_ids.filtered(
            lambda l: l.attribute_id.display_type in ('color', 'image')
        )
        if visual_line:
            return visual_line[0].action_manage_visuals()
        return False
