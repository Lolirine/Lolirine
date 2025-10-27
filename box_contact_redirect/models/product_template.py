# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    box_require_contact = fields.Boolean(
        string='Rediriger vers contact',
        default=False,
        help="Si coché, le bouton 'Ajouter au panier' sera remplacé par un bouton 'Nous contacter' sur le site web"
    )
    
    box_is_available = fields.Boolean(
        string='Box disponible',
        default=True,
        help="Indique si le box est actuellement disponible à la location"
    )
