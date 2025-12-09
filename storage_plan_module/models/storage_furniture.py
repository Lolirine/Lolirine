# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StorageFurnitureCategory(models.Model):
    _name = 'storage.furniture.category'
    _description = 'Catégorie de meubles'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True)
    icon = fields.Char(string='Icône CSS', default='fa-couch',
                       help="Classe Font Awesome pour l'icône (ex: fa-couch, fa-bed)")
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(string='Actif', default=True)
    furniture_ids = fields.One2many('storage.furniture.type', 'category_id', string='Meubles')
    
    furniture_count = fields.Integer(string='Nombre de meubles', compute='_compute_furniture_count')
    
    @api.depends('furniture_ids')
    def _compute_furniture_count(self):
        for cat in self:
            cat.furniture_count = len(cat.furniture_ids)


class StorageFurnitureType(models.Model):
    _name = 'storage.furniture.type'
    _description = 'Type de meuble pour estimation volume'
    _order = 'category_id, sequence, name'

    name = fields.Char(string='Nom', required=True)
    category_id = fields.Many2one('storage.furniture.category', string='Catégorie', required=True)
    
    # Dimensions en centimètres
    width = fields.Float(string='Largeur (cm)', required=True, default=100)
    depth = fields.Float(string='Profondeur (cm)', required=True, default=50)
    height = fields.Float(string='Hauteur (cm)', required=True, default=80)
    
    # Volume calculé
    volume = fields.Float(string='Volume (m³)', compute='_compute_volume', store=True)
    
    # Couleur pour la visualisation 3D (format hex)
    color_3d = fields.Char(string='Couleur 3D', default='#3498db',
                           help="Couleur hexadécimale pour la visualisation 3D")
    
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(string='Actif', default=True)
    
    # Icône personnalisée (optionnel)
    icon = fields.Char(string='Icône', help="Emoji ou icône pour affichage")
    
    @api.depends('width', 'depth', 'height')
    def _compute_volume(self):
        for furniture in self:
            # Conversion cm³ en m³
            furniture.volume = (furniture.width * furniture.depth * furniture.height) / 1000000
    
    def get_furniture_data(self):
        """Retourne les données du meuble pour le frontend"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id.id,
            'category_name': self.category_id.name,
            'width': self.width,
            'depth': self.depth,
            'height': self.height,
            'volume': round(self.volume, 3),
            'color': self.color_3d or '#3498db',
            'icon': self.icon or '',
        }
