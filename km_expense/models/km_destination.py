# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

# Essayer d'importer requests pour l'API de calcul de distance
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class KmLieuDepart(models.Model):
    """Lieux de départ prédéfinis (siège social, hangar, etc.)"""
    _name = 'km.lieu.depart'
    _description = 'Lieu de Départ'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code', required=True)
    adresse = fields.Char(string='Adresse', required=True)
    code_postal = fields.Char(string='Code Postal', required=True)
    ville = fields.Char(string='Ville', required=True)
    pays_id = fields.Many2one('res.country', string='Pays', default=lambda self: self.env.ref('base.be'))
    
    adresse_complete = fields.Char(
        string='Adresse complète',
        compute='_compute_adresse_complete',
        store=True,
    )
    
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(string='Par défaut', default=False)
    
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
    )

    @api.depends('adresse', 'code_postal', 'ville', 'pays_id')
    def _compute_adresse_complete(self):
        for lieu in self:
            parts = [lieu.adresse, lieu.code_postal, lieu.ville]
            if lieu.pays_id:
                parts.append(lieu.pays_id.name)
            lieu.adresse_complete = ', '.join(filter(None, parts))

    @api.model
    def get_default(self):
        """Retourne le lieu de départ par défaut"""
        return self.search([('is_default', '=', True)], limit=1)


class KmDestination(models.Model):
    """Destinations favorites (fournisseurs, clients, etc.)"""
    _name = 'km.destination'
    _description = 'Destination Favorite'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    
    # Adresse
    adresse = fields.Char(string='Adresse', required=True)
    code_postal = fields.Char(string='Code Postal', required=True)
    ville = fields.Char(string='Ville', required=True)
    pays_id = fields.Many2one('res.country', string='Pays', default=lambda self: self.env.ref('base.be'))
    
    adresse_complete = fields.Char(
        string='Adresse complète',
        compute='_compute_adresse_complete',
        store=True,
    )
    
    # Type de destination
    type_destination = fields.Selection([
        ('fournisseur', 'Fournisseur'),
        ('client', 'Client'),
        ('administratif', 'Administratif'),
        ('autre', 'Autre'),
    ], string='Type', default='fournisseur', required=True)
    
    # Lien avec res.partner (optionnel)
    partner_id = fields.Many2one('res.partner', string='Contact associé')
    
    # Distances prédéfinies depuis chaque lieu de départ
    distance_ids = fields.One2many(
        'km.destination.distance',
        'destination_id',
        string='Distances',
    )
    
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
    )

    @api.depends('adresse', 'code_postal', 'ville', 'pays_id')
    def _compute_adresse_complete(self):
        for dest in self:
            parts = [dest.adresse, dest.code_postal, dest.ville]
            if dest.pays_id:
                parts.append(dest.pays_id.name)
            dest.adresse_complete = ', '.join(filter(None, parts))

    def get_distance_from(self, lieu_depart_id):
        """Retourne la distance depuis un lieu de départ donné"""
        self.ensure_one()
        distance = self.distance_ids.filtered(lambda d: d.lieu_depart_id.id == lieu_depart_id)
        return distance.distance_km if distance else 0.0


class KmDestinationDistance(models.Model):
    """Distances entre un lieu de départ et une destination"""
    _name = 'km.destination.distance'
    _description = 'Distance Lieu-Destination'
    _rec_name = 'destination_id'

    destination_id = fields.Many2one(
        'km.destination',
        string='Destination',
        required=True,
        ondelete='cascade',
    )
    lieu_depart_id = fields.Many2one(
        'km.lieu.depart',
        string='Lieu de départ',
        required=True,
        ondelete='cascade',
    )
    distance_km = fields.Float(
        string='Distance (km)',
        digits=(10, 1),
        required=True,
    )
    distance_aller_retour = fields.Float(
        string='Aller-Retour (km)',
        compute='_compute_aller_retour',
        store=True,
    )

    @api.depends('distance_km')
    def _compute_aller_retour(self):
        for record in self:
            record.distance_aller_retour = record.distance_km * 2

    _sql_constraints = [
        ('unique_destination_depart',
         'UNIQUE(destination_id, lieu_depart_id)',
         'Une distance existe déjà pour ce couple lieu de départ / destination!')
    ]


class KmDistanceCalculator(models.AbstractModel):
    """Service de calcul de distance via API"""
    _name = 'km.distance.calculator'
    _description = 'Calculateur de Distance'

    @api.model
    def calculate_distance(self, origin, destination):
        """
        Calcule la distance entre deux adresses.
        Utilise OpenRouteService (gratuit) ou Google Distance Matrix API
        
        :param origin: Adresse de départ (string)
        :param destination: Adresse d'arrivée (string)
        :return: Distance en km (float) ou 0.0 si erreur
        """
        if not REQUESTS_AVAILABLE:
            _logger.warning("Module 'requests' non disponible pour le calcul de distance")
            return 0.0

        # Récupérer la clé API depuis les paramètres système
        api_key = self.env['ir.config_parameter'].sudo().get_param('km_expense.distance_api_key', '')
        api_provider = self.env['ir.config_parameter'].sudo().get_param('km_expense.distance_api_provider', 'openroute')

        if not api_key:
            _logger.info("Pas de clé API configurée pour le calcul de distance")
            return 0.0

        try:
            if api_provider == 'google':
                return self._calculate_google(origin, destination, api_key)
            else:
                return self._calculate_openroute(origin, destination, api_key)
        except Exception as e:
            _logger.error(f"Erreur lors du calcul de distance: {e}")
            return 0.0

    def _calculate_openroute(self, origin, destination, api_key):
        """Calcul via OpenRouteService (gratuit, 2000 requêtes/jour)"""
        # D'abord, géocoder les adresses
        geocode_url = "https://api.openrouteservice.org/geocode/search"
        
        # Géocoder l'origine
        response = requests.get(geocode_url, params={
            'api_key': api_key,
            'text': origin,
            'size': 1,
        }, timeout=10)
        origin_data = response.json()
        if not origin_data.get('features'):
            return 0.0
        origin_coords = origin_data['features'][0]['geometry']['coordinates']
        
        # Géocoder la destination
        response = requests.get(geocode_url, params={
            'api_key': api_key,
            'text': destination,
            'size': 1,
        }, timeout=10)
        dest_data = response.json()
        if not dest_data.get('features'):
            return 0.0
        dest_coords = dest_data['features'][0]['geometry']['coordinates']
        
        # Calculer la route
        directions_url = "https://api.openrouteservice.org/v2/directions/driving-car"
        response = requests.get(directions_url, params={
            'api_key': api_key,
            'start': f"{origin_coords[0]},{origin_coords[1]}",
            'end': f"{dest_coords[0]},{dest_coords[1]}",
        }, timeout=10)
        route_data = response.json()
        
        if route_data.get('features'):
            distance_m = route_data['features'][0]['properties']['segments'][0]['distance']
            return round(distance_m / 1000, 1)
        
        return 0.0

    def _calculate_google(self, origin, destination, api_key):
        """Calcul via Google Distance Matrix API"""
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        
        response = requests.get(url, params={
            'origins': origin,
            'destinations': destination,
            'key': api_key,
            'units': 'metric',
        }, timeout=10)
        
        data = response.json()
        
        if data.get('status') == 'OK':
            element = data['rows'][0]['elements'][0]
            if element.get('status') == 'OK':
                distance_m = element['distance']['value']
                return round(distance_m / 1000, 1)
        
        return 0.0
