from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_colisage = fields.Integer(
        string="Colisage (pièces/colis)",
        default=1,
        help="Quantité par colis. Si supérieur à 1, le produit ne peut être "
             "commandé sur le site que par multiples de cette valeur "
             "(la quantité ajoutée au panier est arrondie au multiple supérieur).",
    )
