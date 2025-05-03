from odoo import models, fields

class TrajetIntervention(models.Model):
    _name = 'trajet.intervention'
    _description = 'Trajet Intervention'

    name = fields.Char(string="Nom", required=True)
    date = fields.Date(string="Date d'intervention")
    location = fields.Char(string="Lieu d'intervention")
    completed = fields.Boolean(string="Terminé")
