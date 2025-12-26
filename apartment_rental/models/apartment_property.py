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
    
    # Données cadastrales
    cadastral_division = fields.Char(string='Division cadastrale')
    cadastral_section = fields.Char(string='Section')
    cadastral_parcel = fields.Char(string='N° parcelle')
    cadastral_reference = fields.Char(string='Réf. dossier cadastre')
    cadastral_surface = fields.Float(string='Surface cadastrale (m²)')
    construction_year = fields.Integer(string='Année de construction')
    building_permit_date = fields.Date(string='Date permis d\'urbanisme')
    building_permit_ref = fields.Char(string='Réf. permis d\'urbanisme')
    
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
    # Aliases for view compatibility
    num_rooms = fields.Integer(related='nb_rooms', string='Nombre de pièces')
    num_bedrooms = fields.Integer(related='nb_bedrooms', string='Nombre de chambres')
    num_bathrooms = fields.Integer(related='nb_bathrooms', string='Nombre de salles de bain')
    floor = fields.Integer(string='Étage')
    has_elevator = fields.Boolean(string='Ascenseur')
    has_parking = fields.Boolean(string='Parking')
    has_garage = fields.Boolean(string='Garage')
    has_cellar = fields.Boolean(string='Cave')
    has_garden = fields.Boolean(string='Jardin')
    has_terrace = fields.Boolean(string='Terrasse')
    has_balcony = fields.Boolean(string='Balcon')
    
    # PEB - Certificat
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
    peb_certificate = fields.Char(string='Référence PEB')
    peb_number = fields.Char(string='Numéro PEB')
    peb_date = fields.Date(string='Date établissement PEB')
    peb_expiry_date = fields.Date(string='Date d\'expiration PEB')
    peb_responsible = fields.Char(string='Responsable PEB')
    peb_responsible_number = fields.Char(string='N° agrément responsable PEB')
    
    # PEB - Performance énergétique
    peb_consumption_total = fields.Float(string='Consommation totale (kWh/an)')
    peb_consumption_specific = fields.Float(string='Consommation spécifique (kWh/m².an)')
    peb_espec = fields.Integer(string='Espec')
    peb_ew = fields.Integer(string='Niveau Ew')
    peb_k = fields.Integer(string='Niveau K')
    peb_co2_annual = fields.Float(string='Émissions CO2 (kg/an)')
    peb_co2_specific = fields.Float(string='Émissions CO2 spécifiques (kg/m².an)')
    peb_volume = fields.Float(string='Volume protégé (m³)')
    peb_heated_surface = fields.Float(string='Surface plancher chauffée (m²)')
    
    # Chauffage
    heating_type = fields.Selection([
        ('gas', 'Gaz naturel'),
        ('propane', 'Propane'),
        ('electric', 'Électrique'),
        ('oil', 'Mazout'),
        ('heat_pump', 'Pompe à chaleur'),
        ('pellet', 'Pellets'),
        ('other', 'Autre'),
    ], string='Type de chauffage')
    heating_system = fields.Selection([
        ('central', 'Chauffage central'),
        ('individual', 'Chauffage individuel'),
        ('collective', 'Chauffage collectif'),
        ('floor', 'Chauffage au sol'),
        ('radiators', 'Radiateurs'),
        ('convectors', 'Convecteurs'),
    ], string='Système de chauffage')
    heating_distribution = fields.Char(string='Distribution chauffage')
    has_thermostat = fields.Boolean(string='Vannes thermostatiques')
    
    # Eau chaude sanitaire
    hot_water_system = fields.Selection([
        ('boiler', 'Chaudière'),
        ('boiler_tank', 'Chaudière + ballon'),
        ('electric', 'Électrique'),
        ('heat_pump', 'Pompe à chaleur'),
        ('solar', 'Solaire'),
    ], string='Production ECS')
    hot_water_tank_capacity = fields.Integer(string='Capacité ballon ECS (L)')
    
    # Ventilation
    ventilation_type = fields.Selection([
        ('none', 'Aucune'),
        ('natural', 'Naturelle'),
        ('a', 'Système A'),
        ('b', 'Système B'),
        ('c', 'Système C'),
        ('d', 'Système D'),
    ], string='Système de ventilation')
    
    # Énergies renouvelables
    has_solar_thermal = fields.Boolean(string='Solaire thermique')
    has_solar_pv = fields.Boolean(string='Panneaux photovoltaïques')
    has_heat_pump = fields.Boolean(string='Pompe à chaleur')
    
    # Finances
    monthly_rent = fields.Float(string='Loyer mensuel indicatif (€)')
    monthly_charges = fields.Float(string='Charges mensuelles indicatives (€)')
    cadastral_income = fields.Float(string='Revenu cadastral (€)')
    
    # Équipements
    equipment_ids = fields.Many2many(
        'apartment.equipment',
        string='Équipements',
    )
    equipment = fields.Text(string='Équipements (description)')
    description = fields.Html(string='Description')
    notes = fields.Text(string='Notes internes')
    
    # Photos
    image_main = fields.Image(string='Photo principale', max_width=1920, max_height=1920)
    image_ids = fields.One2many(
        'apartment.property.image',
        'property_id',
        string='Photos',
    )
    initial_photo_ids = fields.One2many(
        'apartment.property.initial.photo',
        'property_id',
        string='Photos initiales',
    )
    initial_photo_count = fields.Integer(
        string='Nombre de photos initiales',
        compute='_compute_initial_photo_count',
    )
    initial_photo_date = fields.Date(
        string='Date des photos initiales',
        help='Date à laquelle les photos initiales ont été prises',
    )
    
    # Contrats d'entretien
    maintenance_contract_ids = fields.One2many(
        'apartment.maintenance.contract',
        'property_id',
        string='Contrats d\'entretien',
    )
    maintenance_contract_count = fields.Integer(
        string='Nombre de contrats',
        compute='_compute_maintenance_contract_count',
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
    current_tenant_id = fields.Many2one(
        'apartment.tenant',
        string='Locataire actuel',
        related='current_lease_id.tenant_id',
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

    def _compute_initial_photo_count(self):
        for record in self:
            record.initial_photo_count = len(record.initial_photo_ids)

    def _compute_maintenance_contract_count(self):
        for record in self:
            record.maintenance_contract_count = len(record.maintenance_contract_ids)

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

    def action_view_initial_photos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Photos initiales'),
            'res_model': 'apartment.property.initial.photo',
            'view_mode': 'kanban,list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_view_maintenance_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrats d\'entretien'),
            'res_model': 'apartment.maintenance.contract',
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


class ApartmentPropertyInitialPhoto(models.Model):
    _name = 'apartment.property.initial.photo'
    _description = 'Photo initiale du bien'
    _order = 'room_type_id, sequence, id'

    property_id = fields.Many2one(
        'apartment.property',
        string='Bien',
        required=True,
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
    
    # Localisation
    room_type_id = fields.Many2one(
        'apartment.room.type',
        string='Pièce',
    )
    location_detail = fields.Char(string='Détail emplacement')
    
    # Type de photo
    photo_type = fields.Selection([
        ('general', 'Vue générale'),
        ('detail', 'Détail'),
        ('equipment', 'Équipement'),
        ('meter', 'Compteur'),
        ('exterior', 'Extérieur'),
        ('common_area', 'Parties communes'),
        ('other', 'Autre'),
    ], string='Type', default='general')
    
    # Métadonnées
    taken_date = fields.Date(
        string='Date de prise',
        default=fields.Date.today,
    )
    taken_by = fields.Many2one(
        'res.users',
        string='Prise par',
        default=lambda self: self.env.user,
    )
    
    # Notes
    notes = fields.Text(string='Notes')
