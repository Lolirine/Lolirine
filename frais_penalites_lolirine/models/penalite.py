from odoo import models, fields

class Penalite(models.Model):
    _name = 'fraispenalite.penalite'
    _description = 'Frais et pénalité liés à un abonnement'

    name = fields.Char(string='Description', required=True)
    partner_id = fields.Many2one('res.partner', string='Client', required=True)
    subscription_id = fields.Many2one('sale.subscription', string='Abonnement', required=True)
    product_id = fields.Many2one('product.product', string='Produit de pénalité', required=True)
    price_unit = fields.Float(string='Prix unitaire', related='product_id.list_price', store=True)
    date = fields.Date(string='Date', default=fields.Date.context_today)
    invoice_id = fields.Many2one('account.move', string='Facture')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('invoiced', 'Facturé'),
        ('cancelled', 'Annulé')
    ], string='État', default='draft')
