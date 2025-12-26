# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ApartmentInventoryLine(models.Model):
    _name = 'apartment.inventory.line'
    _description = 'Ligne d\'état des lieux'
    _order = 'sequence, id'

    inventory_id = fields.Many2one(
        'apartment.inventory',
        string='État des lieux',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    
    # Pièce
    room_type_id = fields.Many2one(
        'apartment.room.type',
        string='Type de pièce',
    )
    name = fields.Char(string='Pièce', required=True)
    
    # État actuel
    condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
        ('na', 'N/A'),
    ], string='État', default='good')
    
    # Détails par élément
    walls_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
        ('na', 'N/A'),
    ], string='Murs', default='good')
    walls_notes = fields.Text(string='Notes murs')
    walls_color = fields.Char(string='Couleur murs')
    
    ceiling_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
        ('na', 'N/A'),
    ], string='Plafond', default='good')
    ceiling_notes = fields.Text(string='Notes plafond')
    
    floor_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
        ('na', 'N/A'),
    ], string='Sol', default='good')
    floor_type = fields.Selection([
        ('parquet', 'Parquet'),
        ('laminate', 'Stratifié'),
        ('tiles', 'Carrelage'),
        ('carpet', 'Moquette'),
        ('vinyl', 'Vinyle'),
        ('concrete', 'Béton'),
        ('other', 'Autre'),
    ], string='Type de sol')
    floor_notes = fields.Text(string='Notes sol')
    
    windows_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
        ('na', 'N/A'),
    ], string='Fenêtres', default='good')
    windows_count = fields.Integer(string='Nombre de fenêtres')
    windows_notes = fields.Text(string='Notes fenêtres')
    
    doors_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
        ('na', 'N/A'),
    ], string='Portes', default='good')
    doors_notes = fields.Text(string='Notes portes')
    
    electricity_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
        ('na', 'N/A'),
    ], string='Électricité', default='good')
    electricity_notes = fields.Text(string='Notes électricité')
    outlets_count = fields.Integer(string='Nombre de prises')
    switches_count = fields.Integer(string='Nombre d\'interrupteurs')
    
    heating_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
        ('na', 'N/A'),
    ], string='Chauffage', default='good')
    heating_type = fields.Selection([
        ('radiator', 'Radiateur'),
        ('floor', 'Sol chauffant'),
        ('convector', 'Convecteur'),
        ('none', 'Aucun'),
        ('other', 'Autre'),
    ], string='Type de chauffage')
    heating_notes = fields.Text(string='Notes chauffage')
    
    # Équipements spécifiques (cuisine, salle de bain)
    has_sink = fields.Boolean(string='Évier/Lavabo')
    sink_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État évier')
    
    has_toilet = fields.Boolean(string='WC')
    toilet_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État WC')
    
    has_shower = fields.Boolean(string='Douche')
    shower_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État douche')
    
    has_bathtub = fields.Boolean(string='Baignoire')
    bathtub_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État baignoire')
    
    # Électroménager
    has_oven = fields.Boolean(string='Four')
    oven_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État four')
    oven_brand = fields.Char(string='Marque four')
    
    has_cooktop = fields.Boolean(string='Plaque de cuisson')
    cooktop_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État plaque')
    cooktop_type = fields.Selection([
        ('gas', 'Gaz'),
        ('electric', 'Électrique'),
        ('induction', 'Induction'),
        ('vitro', 'Vitrocéramique'),
    ], string='Type plaque')
    
    has_hood = fields.Boolean(string='Hotte')
    hood_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État hotte')
    
    has_dishwasher = fields.Boolean(string='Lave-vaisselle')
    dishwasher_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État lave-vaisselle')
    
    has_fridge = fields.Boolean(string='Réfrigérateur')
    fridge_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
    ], string='État réfrigérateur')
    
    # Notes générales
    notes = fields.Text(string='Observations')
    damages = fields.Text(string='Dégâts constatés')
    
    # Comparaison avec entrée (pour état de sortie)
    entry_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Bon'),
        ('fair', 'Correct'),
        ('poor', 'Mauvais'),
        ('very_poor', 'Très mauvais'),
        ('na', 'N/A'),
    ], string='État à l\'entrée')
    entry_notes = fields.Text(string='Notes à l\'entrée')
    degradation = fields.Boolean(
        string='Dégradation',
        compute='_compute_degradation',
        store=True,
    )
    
    # Photos de la pièce
    photo_ids = fields.One2many(
        'apartment.inventory.photo',
        'line_id',
        string='Photos',
    )

    @api.depends('condition', 'entry_condition')
    def _compute_degradation(self):
        condition_order = {
            'excellent': 5,
            'good': 4,
            'fair': 3,
            'poor': 2,
            'very_poor': 1,
            'na': 0,
            False: 0,
        }
        for record in self:
            if record.entry_condition and record.condition:
                record.degradation = condition_order.get(record.condition, 0) < condition_order.get(record.entry_condition, 0)
            else:
                record.degradation = False
