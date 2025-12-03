# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StorageStatusColor(models.Model):
    _name = 'storage.status.color'
    _description = 'Couleurs des statuts'
    _order = 'sequence'

    name = fields.Char(string='Libellé', required=True)
    status_key = fields.Selection([
        ('disponible', 'Disponible'),
        ('occupe', 'Occupé'),
        ('maintenance', 'Maintenance'),
        ('nettoyage', 'Nettoyage'),
        ('reserve', 'Réservé'),
        ('bientot_dispo', 'Bientôt disponible'),
        ('inspection', 'En inspection'),
        ('technique', 'Technique'),
    ], string='Statut', required=True)
    color = fields.Char(string='Couleur (hex)', required=True, default='#FFFFFF',
                        help="Code couleur hexadécimal (ex: #90EE90)")
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(string='Actif', default=True)
    show_in_legend = fields.Boolean(string='Afficher dans la légende', default=True)

    _sql_constraints = [
        ('status_key_unique', 'unique(status_key)', 'Ce statut a déjà une couleur définie!')
    ]

    @api.model
    def get_color_for_status(self, status_key):
        """Retourne la couleur pour un statut donné"""
        record = self.search([('status_key', '=', status_key), ('active', '=', True)], limit=1)
        if record:
            return record.color
        # Couleurs par défaut
        default_colors = {
            'disponible': '#90EE90',
            'occupe': '#FFB6C1',
            'maintenance': '#FFFF99',
            'nettoyage': '#87CEEB',
            'reserve': '#FFE4B5',
            'bientot_dispo': '#E6E6FA',
            'inspection': '#B0C4DE',
            'technique': '#D3D3D3',
        }
        return default_colors.get(status_key, '#FFFFFF')

    @api.model
    def get_legend_items(self):
        """Retourne les éléments de la légende"""
        records = self.search([('active', '=', True), ('show_in_legend', '=', True)], order='sequence')
        if records:
            return [{
                'status': r.status_key,
                'label': r.name,
                'color': r.color,
            } for r in records]
        # Légende par défaut
        return [
            {'status': 'occupe', 'label': 'Occupé', 'color': '#FFB6C1'},
            {'status': 'disponible', 'label': 'Disponible', 'color': '#90EE90'},
            {'status': 'maintenance', 'label': 'Maintenance', 'color': '#FFFF99'},
            {'status': 'nettoyage', 'label': 'Nettoyage', 'color': '#87CEEB'},
            {'status': 'reserve', 'label': 'Réservé', 'color': '#FFE4B5'},
            {'status': 'bientot_dispo', 'label': 'Bientôt dispo.', 'color': '#E6E6FA'},
            {'status': 'inspection', 'label': 'En inspection', 'color': '#B0C4DE'},
            {'status': 'technique', 'label': 'Technique', 'color': '#D3D3D3'},
        ]
