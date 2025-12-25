# -*- coding: utf-8 -*-

from odoo import models, fields, _


class ApartmentRoomType(models.Model):
    _name = 'apartment.room.type'
    _description = 'Type de pièce'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    code = fields.Char(string='Code')
    
    # Éléments à vérifier par défaut
    check_walls = fields.Boolean(string='Vérifier murs', default=True)
    check_ceiling = fields.Boolean(string='Vérifier plafond', default=True)
    check_floor = fields.Boolean(string='Vérifier sol', default=True)
    check_windows = fields.Boolean(string='Vérifier fenêtres', default=True)
    check_doors = fields.Boolean(string='Vérifier portes', default=True)
    check_electricity = fields.Boolean(string='Vérifier électricité', default=True)
    check_heating = fields.Boolean(string='Vérifier chauffage', default=True)
    
    # Spécifique cuisine
    is_kitchen = fields.Boolean(string='Est une cuisine')
    # Spécifique salle de bain
    is_bathroom = fields.Boolean(string='Est une salle de bain/WC')
    
    description = fields.Text(string='Description')
