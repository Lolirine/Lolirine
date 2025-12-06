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
    color = fields.Integer(string='Couleur', default=0,
                           help="Couleur Odoo standard (0-11)")
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(string='Actif', default=True)
    show_in_legend = fields.Boolean(string='Afficher dans la légende', default=True)

    _sql_constraints = [
        ('status_key_unique', 'unique(status_key)', 'Ce statut a déjà une couleur définie!')
    ]

    def _get_color_hex(self):
        """Convertit l'index de couleur Odoo en code hexadécimal"""
        # Mapping des couleurs Odoo standard vers hex
        color_map = {
            0: '#FFFFFF',   # Blanc/Gris clair
            1: '#F06050',   # Rouge
            2: '#F4A460',   # Orange
            3: '#F7CD1F',   # Jaune
            4: '#6CC1ED',   # Bleu clair
            5: '#814968',   # Violet foncé
            6: '#EB7E7F',   # Rose/Rouge clair
            7: '#2C8397',   # Bleu moyen
            8: '#475577',   # Bleu foncé
            9: '#D6145F',   # Fuchsia/Magenta
            10: '#30C381',  # Vert
            11: '#9365B8',  # Violet
        }
        return color_map.get(self.color, '#FFFFFF')

    @api.model
    def get_color_for_status(self, status_key):
        """Retourne la couleur hex pour un statut donné"""
        record = self.search([('status_key', '=', status_key), ('active', '=', True)], limit=1)
        if record:
            return record._get_color_hex()
        # Couleurs par défaut
        default_colors = {
            'disponible': '#30C381',   # Vert (10)
            'occupe': '#F06050',       # Rouge (1)
            'maintenance': '#F7CD1F',  # Jaune (3)
            'nettoyage': '#6CC1ED',    # Bleu clair (4)
            'reserve': '#F4A460',      # Orange (2)
            'bientot_dispo': '#9365B8', # Violet (11)
            'inspection': '#2C8397',   # Bleu moyen (7)
            'technique': '#475577',    # Bleu foncé (8)
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
                'color': r._get_color_hex(),
            } for r in records]
        # Légende par défaut
        return [
            {'status': 'disponible', 'label': 'Disponible', 'color': '#30C381'},
            {'status': 'occupe', 'label': 'Occupé', 'color': '#F06050'},
            {'status': 'maintenance', 'label': 'Maintenance', 'color': '#F7CD1F'},
            {'status': 'nettoyage', 'label': 'Nettoyage', 'color': '#6CC1ED'},
            {'status': 'reserve', 'label': 'Réservé', 'color': '#F4A460'},
            {'status': 'bientot_dispo', 'label': 'Bientôt dispo.', 'color': '#9365B8'},
            {'status': 'inspection', 'label': 'En inspection', 'color': '#2C8397'},
            {'status': 'technique', 'label': 'Technique', 'color': '#475577'},
        ]
