from odoo import models, fields

class VisiteBox(models.Model):
    _name = 'visite.box'
    _description = 'Visite de box garde-meubles'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Nom du client", required=True)
    email = fields.Char("Email")
    phone = fields.Char("Téléphone")
    date_visite = fields.Datetime("Date de la visite", required=True)
    type_box = fields.Selection([
        ('petit', 'Petit'),
        ('moyen', 'Moyen'),
        ('grand', 'Grand')
    ], string="Taille souhaitée", required=True)
    state = fields.Selection(
        [('draft', 'À confirmer'), ('confirmed', 'Confirmée'), ('done', 'Réalisée')],
        default='draft', string="Statut", tracking=True
    )
    signature = fields.Binary("Signature du client")
