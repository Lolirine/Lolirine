
from odoo import models, fields

class PenaliteClient(models.Model):
    _name = "penalite.client"
    _description = "Pénalité Client"

    partner_id = fields.Many2one('res.partner', string="Client", required=True)
    montant = fields.Float(string="Montant")
    motif = fields.Char(string="Motif")
    date = fields.Date(string="Date", default=fields.Date.today)
    statut = fields.Selection([('non_paye', 'Non payé'), ('paye', 'Payé')], string="Statut", default='non_paye')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    penalite_ids = fields.One2many('penalite.client', 'partner_id', string="Pénalités")
    test_field = fields.Char(string="Champ Test Pénalité")
