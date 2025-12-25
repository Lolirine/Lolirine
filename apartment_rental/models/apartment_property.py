# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApartmentProperty(models.Model):
    _name = 'apartment.property'
    _description = 'Bien Immobilier'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Nom du bien',
        required=True,
        tracking=True,
    )
    reference = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )
    active = fields.Boolean(default=True)
    
    # Localisation
    street = fields.Char(string='Rue')
    street2 = fields.Char(string='Complément d\'adresse')
    zip_code = fields.Char(string='Code postal')
    city = fields.Char(string='Ville')
    country_id = fields.Many2one(
        'res.country',
        string='Pays',
        default=lambda self: self.env.ref('base.be', raise_if_not_found=False),
    )
    
    # Caractéristiques
    property_type = fields.Selection([
        ('apartment', 'Appartement'),
        ('house', 'Maison'),
        ('studio', 'Studio'),
        ('loft', 'Loft'),
        ('other', 'Autre'),
    ], string='Type de bien', default='apartment', tracking=True)
    
    surface = fields.Float(string='Surface habitable (m²)')
    nb_rooms = fields.Integer(string='Nombre de pièces')
    nb_bedrooms = fields.Integer(string='Nombre de chambres')
    nb_bathrooms = fields.Integer(string='Nombre de salles de bain')
    floor = fields.Integer(string='Étage')
    has_elevator = fields.Boolean(string='Ascenseur')
    has_parking = fields.Boolean(string='Parking')
    has_garage = fields.Boolean(string='Garage')
    has_cellar = fields.Boolean(string='Cave')
    has_garden = fields.Boolean(string='Jardin')
    has_terrace = fields.Boolean(string='Terrasse')
    has_balcony = fields.Boolean(string='Balcon')
    
    # Énergie
    energy_class = fields.Selection([
        ('a++', 'A++'),
        ('a+', 'A+'),
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
        ('d', 'D'),
        ('e', 'E'),
        ('f', 'F'),
        ('g', 'G'),
    ], string='Classe énergétique (PEB)')
    peb_certificate = fields.Char(string='N° certificat PEB')
    heating_type = fields.Selection([
        ('gas', 'Gaz'),
        ('electric', 'Électrique'),
        ('oil', 'Mazout'),
        ('heat_pump', 'Pompe à chaleur'),
        ('pellet', 'Pellets'),
        ('other', 'Autre'),
    ], string='Type de chauffage')
    
    # Équipements
    equipment_ids = fields.Many2many(
        'apartment.equipment',
        string='Équipements',
    )
    description = fields.Html(string='Description')
    notes = fields.Text(string='Notes internes')
    
    # Photos
    image_main = fields.Image(string='Photo principale', max_width=1920, max_height=1920)
    image_ids = fields.One2many(
        'apartment.property.image',
        'property_id',
        string='Photos',
    )
    
    # Relations
    lease_ids = fields.One2many(
        'apartment.lease',
        'property_id',
        string='Baux',
    )
    current_lease_id = fields.Many2one(
        'apartment.lease',
        string='Bail en cours',
        compute='_compute_current_lease',
        store=True,
    )
    inventory_ids = fields.One2many(
        'apartment.inventory',
        'property_id',
        string='États des lieux',
    )
    control_visit_ids = fields.One2many(
        'apartment.control.visit',
        'property_id',
        string='Visites de contrôle',
    )
    meter_ids = fields.One2many(
        'apartment.meter',
        'property_id',
        string='Compteurs',
    )
    intervention_ids = fields.One2many(
        'apartment.intervention',
        'property_id',
        string='Interventions',
    )
    document_ids = fields.One2many(
        'apartment.document',
        'property_id',
        string='Documents',
    )
    
    # Compteurs
    lease_count = fields.Integer(
        string='Nombre de baux',
        compute='_compute_counts',
    )
    inventory_count = fields.Integer(
        string='Nombre d\'états des lieux',
        compute='_compute_counts',
    )
    visit_count = fields.Integer(
        string='Nombre de visites',
        compute='_compute_counts',
    )
    intervention_count = fields.Integer(
        string='Nombre d\'interventions',
        compute='_compute_counts',
    )
    
    # Statut
    state = fields.Selection([
        ('available', 'Disponible'),
        ('rented', 'Loué'),
        ('maintenance', 'En maintenance'),
    ], string='Statut', default='available', tracking=True, compute='_compute_state', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('apartment.property') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('lease_ids', 'lease_ids.state')
    def _compute_current_lease(self):
        for record in self:
            current = record.lease_ids.filtered(lambda l: l.state == 'active')
            record.current_lease_id = current[:1] if current else False

    @api.depends('current_lease_id')
    def _compute_state(self):
        for record in self:
            if record.current_lease_id:
                record.state = 'rented'
            else:
                record.state = 'available'

    def _compute_counts(self):
        for record in self:
            record.lease_count = len(record.lease_ids)
            record.inventory_count = len(record.inventory_ids)
            record.visit_count = len(record.control_visit_ids)
            record.intervention_count = len(record.intervention_ids)

    def action_view_leases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Baux'),
            'res_model': 'apartment.lease',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_inventories(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('États des lieux'),
            'res_model': 'apartment.inventory',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_visits(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Visites de contrôle'),
            'res_model': 'apartment.control.visit',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_interventions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Interventions'),
            'res_model': 'apartment.intervention',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }


class ApartmentPropertyImage(models.Model):
    _name = 'apartment.property.image'
    _description = 'Photo du bien'
    _order = 'sequence, id'

    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Description')
    sequence = fields.Integer(default=10)
    image = fields.Image(string='Photo', required=True, max_width=1920, max_height=1920)


class ApartmentEquipment(models.Model):
    _name = 'apartment.equipment'
    _description = 'Équipement'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    category = fields.Selection([
        ('kitchen', 'Cuisine'),
        ('bathroom', 'Salle de bain'),
        ('heating', 'Chauffage'),
        ('security', 'Sécurité'),
        ('comfort', 'Confort'),
        ('outdoor', 'Extérieur'),
        ('other', 'Autre'),
    ], string='Catégorie', default='other')
