from odoo import models, fields, api

class TrajetIntervention(models.Model):
    _name = 'trajet.intervention'
    _description = 'Trajet lié à une intervention ou livraison'

    date_trajet = fields.Datetime(string='Date du trajet', required=True)
    conducteur_id = fields.Many2one('res.users', string='Conducteur', required=True)
    client_id = fields.Many2one('res.partner', string='Client concerné')
    box_id = fields.Many2one('product.product', string='Box concerné')
    motif = fields.Selection([
        ('livraison', 'Livraison'),
        ('retrait', 'Retrait'),
        ('entretien', 'Entretien'),
        ('urgence', 'Urgence'),
        ('autre', 'Autre')
    ], string='Motif', required=True)
    distance_km = fields.Float(string='Distance (km)')
    notes = fields.Text(string='Notes')

    @api.model
    def _register_hook(self):
        view_model = self.env['ir.ui.view']
        action_model = self.env['ir.actions.act_window']
        menu_model = self.env['ir.ui.menu']

        form_view = view_model.create({
            'name': "trajet.intervention.form",
            'model': 'trajet.intervention',
            'arch_base': """
<form string="Trajet d'intervention">
    <sheet>
        <group>
            <field name="date_trajet"/>
            <field name="conducteur_id"/>
            <field name="client_id"/>
            <field name="box_id"/>
            <field name="motif"/>
            <field name="distance_km"/>
            <field name="notes"/>
        </group>
    </sheet>
</form>
""",
            'type': 'form',
        })

        tree_view = view_model.create({
            'name': "trajet.intervention.tree",
            'model': 'trajet.intervention',
            'arch_base': """
<tree string="Trajets d'intervention">
    <field name="date_trajet"/>
    <field name="conducteur_id"/>
    <field name="client_id"/>
    <field name="box_id"/>
    <field name="motif"/>
    <field name="distance_km"/>
</tree>
""",
            'type': 'tree',
        })

        action = action_model.create({
            'name': 'Trajets d’intervention',
            'res_model': 'trajet.intervention',
            'view_mode': 'tree,form',
        })

        try:
            website_menu = self.env['ir.ui.menu'].create({'name': 'Interventions', 'sequence': 1})
        except ValueError:
            website_menu = menu_model.create({'name': 'Site Web (Fallback)', 'sequence': 90})

        menu_model.create({
            'name': 'Trajets interventions',
            'parent_id': website_menu.id,
            'action': 'ir.actions.act_window,%d' % action.id,
        })

        return super()._register_hook()
