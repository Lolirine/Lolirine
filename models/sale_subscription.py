# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'

    # Vous pouvez ajouter des champs spécifiques au contrat de bail ici si nécessaire
    # Par exemple :
    # numero_espace_stockage = fields.Char(string="Numéro de l'espace de stockage")
