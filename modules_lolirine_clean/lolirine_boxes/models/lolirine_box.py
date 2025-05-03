from odoo import models, fields

class LolirineBox(models.Model):
    _name = 'lolirine.box'
    _description = 'Box de stockage Lolirine'

    name = fields.Char(string='Nom du box', required=True)
    location = fields.Char(string='Emplacement')
    size = fields.Selection([('small', 'Petit'), ('medium', 'Moyen'), ('large', 'Grand')], string='Taille')
    is_available = fields.Boolean(string='Disponible', default=True)
