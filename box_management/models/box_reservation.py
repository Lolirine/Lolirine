from odoo import models, fields, api

class BoxReservation(models.Model):
    _name = "box.reservation"
    _description = "Réservation de box"

    name = fields.Char(string="Référence", required=True)
    partner_id = fields.Many2one('res.partner', string="Client", required=True)
    date_start = fields.Date(string="Date de début", required=True)
    date_end = fields.Date(string="Date de fin", required=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('cancelled', 'Annulée')
    ], string="Statut", default="draft")
