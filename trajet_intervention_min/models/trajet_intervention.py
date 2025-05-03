from odoo import models, fields

class TrajetIntervention(models.Model):
    _name = 'trajet.intervention'
    _description = 'Test Intervention Minimal'

    name = fields.Char(string='Nom du trajet')
