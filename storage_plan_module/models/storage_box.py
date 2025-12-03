# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StorageBox(models.Model):
    _name = 'storage.box'
    _description = 'Box de stockage'
    _order = 'floor_id, name'

    name = fields.Char(string='Numéro de box', required=True, index=True)
    floor_id = fields.Many2one('storage.floor', string='Étage', required=True)
    
    # Dimensions
    width = fields.Float(string='Largeur (cm)', required=True)
    depth = fields.Float(string='Profondeur (cm)', required=True)
    height = fields.Float(string='Hauteur (cm)', required=True)
    volume = fields.Float(string='Volume (m³)', compute='_compute_volume', store=True)
    surface = fields.Float(string='Surface (m²)', compute='_compute_surface', store=True)
    
    # Informations commerciales
    price_monthly = fields.Float(string='Prix mensuel (€)', required=True)
    registration_fee = fields.Float(string='Frais de dossier (€)', default=15.0)
    deposit_months = fields.Integer(string='Caution (mois)', default=2)
    deposit_amount = fields.Float(string='Montant caution (€)', compute='_compute_deposit')
    
    # Statut
    status = fields.Selection([
        ('disponible', 'Disponible'),
        ('occupe', 'Occupé'),
        ('maintenance', 'Maintenance'),
        ('nettoyage', 'Nettoyage'),
        ('reserve', 'Réservé'),
        ('bientot_dispo', 'Bientôt disponible'),
        ('inspection', 'En inspection'),
        ('technique', 'Technique'),
    ], string='Statut', required=True, default='disponible')
    
    # Date de disponibilité
    date_available = fields.Date(string='Disponible à partir du',
                                  help="Date à laquelle le box sera à nouveau disponible")
    
    # Position sur le plan
    position_x = fields.Float(string='Position X')
    position_y = fields.Float(string='Position Y')
    grid_row = fields.Integer(string='Ligne grille')
    grid_col = fields.Integer(string='Colonne grille')
    aisle = fields.Selection([
        ('left', 'Allée gauche'),
        ('right', 'Allée droite'),
    ], string='Allée', default='left', required=True,
       help="Choisissez dans quelle allée placer le box sur le plan")
    
    # Relations
    reservation_ids = fields.One2many('box.reservation', 'box_id', string='Réservations')
    current_reservation_id = fields.Many2one('box.reservation', string='Réservation actuelle',
                                             compute='_compute_current_reservation')
    
    # Informations supplémentaires
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes internes')
    active = fields.Boolean(string='Actif', default=True)
    
    @api.depends('width', 'depth', 'height')
    def _compute_volume(self):
        for box in self:
            # Conversion cm³ en m³
            box.volume = (box.width * box.depth * box.height) / 1000000 if box.width and box.depth and box.height else 0
    
    @api.depends('width', 'depth')
    def _compute_surface(self):
        for box in self:
            # Conversion cm² en m²
            box.surface = (box.width * box.depth) / 10000 if box.width and box.depth else 0
    
    @api.depends('price_monthly', 'deposit_months')
    def _compute_deposit(self):
        for box in self:
            box.deposit_amount = box.price_monthly * box.deposit_months
    
    @api.depends('reservation_ids', 'reservation_ids.state')
    def _compute_current_reservation(self):
        for box in self:
            current = box.reservation_ids.filtered(
                lambda r: r.state in ['confirmed', 'ongoing'] and r.active
            )
            box.current_reservation_id = current[0] if current else False
    
    def get_status_color(self):
        """Retourne la couleur associée au statut depuis la configuration"""
        StatusColor = self.env['storage.status.color'].sudo()
        return StatusColor.get_color_for_status(self.status)
    
    def action_make_available(self):
        self.status = 'disponible'
    
    def action_make_occupied(self):
        self.status = 'occupe'
    
    def action_make_maintenance(self):
        self.status = 'maintenance'
    
    def action_view_on_website(self):
        """Ouvre la page du plan interactif sur le site web"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/storage/plan',
            'target': 'new',
        }
    
    def get_box_details(self):
        """Retourne les détails du box pour l'affichage web"""
        self.ensure_one()
        # Formater la date de disponibilité
        date_available_str = ''
        if self.date_available:
            date_available_str = self.date_available.strftime('%d/%m/%Y')
        
        return {
            'id': self.id,
            'name': self.name,
            'width': self.width,
            'depth': self.depth,
            'height': self.height,
            'volume': round(self.volume, 1),
            'surface': round(self.surface, 1),
            'price_monthly': self.price_monthly,
            'registration_fee': self.registration_fee,
            'deposit_months': self.deposit_months,
            'deposit_amount': self.deposit_amount,
            'status': self.status,
            'status_label': dict(self._fields['status'].selection).get(self.status),
            'floor': self.floor_id.name,
            'description': self.description or '',
            'aisle': self.aisle or 'left',
            'date_available': date_available_str,
        }
