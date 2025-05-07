from odoo import models, fields

class PenaliteClient(models.Model):
    _name = 'penalite.client'
    _description = "Pénalité Client"

    name = fields.Char(string="Référence", required=True)
    motif = fields.Text(string="Motif")
    montant = fields.Float(string="Montant", required=True)
    date = fields.Date(string="Date de la pénalité", default=fields.Date.today)
