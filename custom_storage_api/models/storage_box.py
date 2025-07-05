# -*- coding: utf-8 -*-
from odoo import models, fields

class StorageBox(models.Model):
    _name = 'storage.box'
    _description = 'Boîte de Stockage'
    _order = 'name'

    name = fields.Char(string="Nom de la boîte", required=True, help="Identifiant unique de la boîte, ex: A-01-01")
    
    state = fields.Selection([
        ('available', 'Disponible'),
        ('occupied', 'Occupé'),
        ('maintenance', 'En maintenance'),
        ('reserved', 'Réservé'),
    ], string="État", default='available', required=True, copy=False)

    color = fields.Integer(string='Index de couleur')

    product_id = fields.Many2one(
        'product.product', 
        string="Produit associé", 
        help="Le produit actuellement dans cette boîte.",
        copy=False
    )
    product_qty = fields.Float(string="Quantité", copy=False)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Le nom de la boîte doit être unique !"),
    ]
