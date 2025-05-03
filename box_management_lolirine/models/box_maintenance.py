from odoo import models, fields

class BoxMaintenance(models.Model):
    _name = "box.maintenance"
    _description = "Maintenance de box"

    box_name = fields.Char(string="Nom du box", required=True)
    date = fields.Date(string="Date de maintenance", required=True)
    type = fields.Selection([
        ('cleaning', 'Nettoyage'),
        ('repair', 'Réparation'),
        ('control', 'Contrôle')
    ], string="Type", required=True)
    notes = fields.Text(string="Remarques")
