from odoo import models, fields

class TrajetIntervention(models.Model):
    _name = 'trajet.intervention'
    _description = 'Trajet lié à une intervention ou livraison'

    date_trajet = fields.Datetime(string='Date du trajet', required=True)
    conducteur_id = fields.Many2one('res.users', string='Conducteur', required=True)
    client_id = fields.Many2one('res.partner', string='Client concerné')
    box_id = fields.Many2one('product.product', string='Box concerné')  # Utilisé comme référence de box
    motif = fields.Selection([
        ('livraison', 'Livraison'),
        ('retrait', 'Retrait'),
        ('entretien', 'Entretien'),
        ('urgence', 'Urgence'),
        ('autre', 'Autre')
    ], string='Motif', required=True)
    distance_km = fields.Float(string='Distance (km)')
    notes = fields.Text(string='Notes')
