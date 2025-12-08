# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StorageBox(models.Model):
    """Box de stockage disponibles"""
    _name = 'storage.box'
    _description = 'Box de stockage'
    _order = 'name'

    name = fields.Char(
        string='Référence',
        required=True,
        index=True
    )
    display_name = fields.Char(
        string='Nom affiché',
        compute='_compute_display_name',
        store=True
    )
    
    # Caractéristiques
    surface = fields.Float(
        string='Surface (m²)',
        required=True
    )
    volume = fields.Float(
        string='Volume (m³)',
        compute='_compute_volume',
        store=True
    )
    hauteur = fields.Float(
        string='Hauteur (m)',
        default=2.5
    )
    largeur = fields.Float(
        string='Largeur (m)'
    )
    profondeur = fields.Float(
        string='Profondeur (m)'
    )
    
    # Emplacement
    etage = fields.Selection([
        ('rdc', 'Rez-de-chaussée'),
        ('1', '1er étage'),
        ('2', '2ème étage'),
        ('ss', 'Sous-sol'),
    ], string='Étage', default='rdc')
    batiment = fields.Char(string='Bâtiment')
    zone = fields.Char(string='Zone')
    
    # État et disponibilité
    state = fields.Selection([
        ('available', 'Disponible'),
        ('reserved', 'Réservée'),
        ('occupied', 'Occupée'),
        ('maintenance', 'En maintenance'),
    ], string='État', default='available', tracking=True)
    
    # Tarification
    prix_mensuel = fields.Monetary(
        string='Prix mensuel HT',
        currency_field='currency_id'
    )
    prix_journalier = fields.Monetary(
        string='Prix journalier HT',
        compute='_compute_prix_journalier',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id
    )
    
    # Caractéristiques spéciales
    climatise = fields.Boolean(string='Climatisée')
    alarme = fields.Boolean(string='Alarme individuelle')
    acces_24h = fields.Boolean(string='Accès 24h/24')
    acces_vehicule = fields.Boolean(string='Accès véhicule')
    plain_pied = fields.Boolean(
        string='Plain-pied',
        compute='_compute_plain_pied',
        store=True
    )
    
    # Relations
    partner_id = fields.Many2one(
        'res.partner',
        string='Client actuel',
        domain=[('is_company', '=', False)]
    )
    visite_ids = fields.Many2many(
        'visite.box',
        'visite_box_storage_box_rel',
        'box_id',
        'visite_id',
        string='Visites'
    )
    
    # Compteurs
    visite_count = fields.Integer(
        string='Nombre de visites',
        compute='_compute_visite_count'
    )
    
    # Produit lié
    product_id = fields.Many2one(
        'product.product',
        string='Produit lié',
        help='Produit utilisé pour la facturation'
    )
    
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    @api.depends('name', 'surface', 'etage')
    def _compute_display_name(self):
        for record in self:
            etage_str = dict(self._fields['etage'].selection).get(record.etage, '')
            record.display_name = f"{record.name} - {record.surface}m² ({etage_str})"

    @api.depends('surface', 'hauteur')
    def _compute_volume(self):
        for record in self:
            record.volume = record.surface * record.hauteur

    @api.depends('prix_mensuel')
    def _compute_prix_journalier(self):
        for record in self:
            record.prix_journalier = record.prix_mensuel / 30 if record.prix_mensuel else 0

    @api.depends('etage')
    def _compute_plain_pied(self):
        for record in self:
            record.plain_pied = record.etage == 'rdc'

    def _compute_visite_count(self):
        for record in self:
            record.visite_count = len(record.visite_ids)

    def action_view_visites(self):
        """Voir les visites pour cette box"""
        self.ensure_one()
        return {
            'name': _('Visites'),
            'type': 'ir.actions.act_window',
            'res_model': 'visite.box',
            'view_mode': 'tree,form,kanban',
            'domain': [('box_ids', 'in', self.id)],
        }

    def action_set_available(self):
        """Marquer comme disponible"""
        self.write({'state': 'available', 'partner_id': False})

    def action_set_maintenance(self):
        """Mettre en maintenance"""
        self.write({'state': 'maintenance'})

    @api.model
    def get_available_boxes(self, surface_min=0, surface_max=0, etage=False):
        """Rechercher les box disponibles selon critères"""
        domain = [('state', '=', 'available')]
        if surface_min:
            domain.append(('surface', '>=', surface_min))
        if surface_max:
            domain.append(('surface', '<=', surface_max))
        if etage:
            domain.append(('etage', '=', etage))
        return self.search(domain)
