from odoo import models, fields, api

class VisiteSite(models.Model):
    _name = 'visite.site'
    _description = 'Visite du site avant location'

    client_id = fields.Many2one('res.partner', string='Client', required=True)
    date_visite = fields.Datetime(string='Date de visite', required=True)
    box_souhaite_id = fields.Many2one('product.product', string='Box souhaité')  # suppose que les boxes sont des produits
    commentaire = fields.Text(string='Commentaire')
    etat = fields.Selection([
        ('planifiee', 'À planifier'),
        ('confirmee', 'Confirmée'),
        ('realisee', 'Réalisée'),
        ('annulee', 'Annulée')
    ], default='planifiee', string='État')
