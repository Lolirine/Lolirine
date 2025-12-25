# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


class ApartmentInventoryPhoto(models.Model):
    _name = 'apartment.inventory.photo'
    _description = 'Photo d\'état des lieux'
    _order = 'sequence, create_date'

    inventory_id = fields.Many2one(
        'apartment.inventory',
        string='État des lieux',
        ondelete='cascade',
    )
    line_id = fields.Many2one(
        'apartment.inventory.line',
        string='Pièce',
        ondelete='cascade',
    )
    
    name = fields.Char(string='Description', required=True)
    sequence = fields.Integer(default=10)
    
    image = fields.Image(
        string='Photo',
        required=True,
        max_width=1920,
        max_height=1920,
    )
    image_thumbnail = fields.Image(
        string='Miniature',
        related='image',
        max_width=256,
        max_height=256,
        store=True,
    )
    
    # Métadonnées
    taken_date = fields.Datetime(
        string='Date de prise',
        default=fields.Datetime.now,
    )
    taken_by = fields.Many2one(
        'res.users',
        string='Prise par',
        default=lambda self: self.env.user,
    )
    
    # Localisation dans le bien
    room_type_id = fields.Many2one(
        'apartment.room.type',
        string='Pièce',
    )
    location_detail = fields.Char(string='Détail emplacement')
    
    # Catégorie
    photo_type = fields.Selection([
        ('general', 'Vue générale'),
        ('detail', 'Détail'),
        ('damage', 'Dégât'),
        ('equipment', 'Équipement'),
        ('meter', 'Compteur'),
        ('key', 'Clé/Badge'),
        ('other', 'Autre'),
    ], string='Type', default='general')
    
    # Annotations
    notes = fields.Text(string='Notes')
    is_damage = fields.Boolean(
        string='Montre un dégât',
        help='Cocher si cette photo documente un dégât',
    )
    damage_description = fields.Text(string='Description du dégât')
    estimated_repair_cost = fields.Float(string='Coût réparation estimé (€)')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = _('Photo %s') % datetime.now().strftime('%Y-%m-%d %H:%M')
        return super().create(vals_list)

    @api.onchange('is_damage')
    def _onchange_is_damage(self):
        if self.is_damage:
            self.photo_type = 'damage'
