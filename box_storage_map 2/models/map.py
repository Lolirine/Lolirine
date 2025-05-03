from odoo import models, fields

class BoxStorageMap(models.Model):
    _name = 'box.storage.map'
    _description = 'Carte de stockage des boxes'

    name = fields.Char("Nom")
    position_x = fields.Integer("Position X")
    position_y = fields.Integer("Position Y")
