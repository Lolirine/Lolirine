from odoo import models, fields, api

class BoxStockage(models.Model):
    _name = 'box.stockage'
    _description = 'Box de stockage'

    name = fields.Char('Code BOX', required=True)
    largeur = fields.Float('Largeur (cm)')
    profondeur = fields.Float('Profondeur (cm)')
    hauteur = fields.Float('Hauteur (cm)')
    volume = fields.Float('Volume (m³)', compute='_compute_volume', store=True)
    cout_mensuel = fields.Float('Coût TVAC (€/mois)')
    etat = fields.Selection([
        ('libre', 'Libre'),
        ('occupe', 'Occupé'),
        ('maintenance', 'Maintenance')
    ], string='État', default='libre')
    x = fields.Integer('Position X (px)')
    y = fields.Integer('Position Y (px)')

    @api.depends('largeur', 'profondeur', 'hauteur')
    def _compute_volume(self):
        for rec in self:
            rec.volume = round((rec.largeur or 0) * (rec.profondeur or 0) * (rec.hauteur or 0) / 1000000, 2)
