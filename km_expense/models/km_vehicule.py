# -*- coding: utf-8 -*-

from odoo import models, fields, api


class KmVehicule(models.Model):
    """Extension du modèle véhicule pour les indemnités kilométriques"""
    _inherit = 'fleet.vehicle'

    puissance_fiscale = fields.Selection([
        ('3', '3 CV et moins'),
        ('4', '4 CV'),
        ('5', '5 CV'),
        ('6', '6 CV'),
        ('7', '7 CV et plus'),
    ], string='Puissance Fiscale', 
       help="Puissance fiscale du véhicule pour le calcul des indemnités kilométriques")
    
    type_vehicule_km = fields.Selection([
        ('voiture', 'Voiture'),
        ('moto', 'Moto (> 50cc)'),
        ('cyclomoteur', 'Cyclomoteur (< 50cc)'),
        ('velo', 'Vélo / VAE'),
    ], string='Type pour IK', default='voiture',
       help="Type de véhicule pour le calcul des indemnités kilométriques")
    
    est_vehicule_personnel = fields.Boolean(
        string='Véhicule Personnel',
        default=False,
        help="Cocher si c'est un véhicule personnel utilisé pour les déplacements professionnels",
    )
    
    proprietaire_id = fields.Many2one(
        'hr.employee',
        string='Propriétaire (Employé)',
        help="Employé propriétaire du véhicule (pour véhicules personnels)",
    )
    
    trajet_ids = fields.One2many(
        'km.trajet',
        'vehicule_id',
        string='Trajets',
    )
    
    total_km_professionnels = fields.Float(
        string='Total KM Professionnels',
        compute='_compute_km_stats',
        store=True,
    )
    
    total_indemnites = fields.Float(
        string='Total Indemnités (€)',
        compute='_compute_km_stats',
        store=True,
    )
    
    nombre_trajets = fields.Integer(
        string='Nombre de Trajets',
        compute='_compute_km_stats',
        store=True,
    )

    @api.depends('trajet_ids', 'trajet_ids.distance', 'trajet_ids.montant_indemnite', 'trajet_ids.state')
    def _compute_km_stats(self):
        for vehicle in self:
            trajets_valides = vehicle.trajet_ids.filtered(lambda t: t.state in ('valide', 'rembourse'))
            vehicle.total_km_professionnels = sum(trajets_valides.mapped('distance'))
            vehicle.total_indemnites = sum(trajets_valides.mapped('montant_indemnite'))
            vehicle.nombre_trajets = len(trajets_valides)

    def action_voir_trajets(self):
        """Ouvre la liste des trajets pour ce véhicule"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Trajets - {self.name}',
            'res_model': 'km.trajet',
            'view_mode': 'list,form,calendar',
            'domain': [('vehicule_id', '=', self.id)],
            'context': {'default_vehicule_id': self.id},
        }


class KmVehiculePersonnel(models.Model):
    """Véhicule personnel pour les employés sans accès au parc auto"""
    _name = 'km.vehicule.personnel'
    _description = 'Véhicule Personnel'
    _order = 'employee_id, name'

    name = fields.Char(
        string='Nom du véhicule',
        required=True,
        help="Ex: Peugeot 308, Renault Clio...",
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Propriétaire',
        required=True,
        default=lambda self: self.env.user.employee_id,
    )
    immatriculation = fields.Char(
        string='Immatriculation',
        required=True,
    )
    marque = fields.Char(string='Marque')
    modele = fields.Char(string='Modèle')
    
    puissance_fiscale = fields.Selection([
        ('3', '3 CV et moins'),
        ('4', '4 CV'),
        ('5', '5 CV'),
        ('6', '6 CV'),
        ('7', '7 CV et plus'),
    ], string='Puissance Fiscale', required=True)
    
    type_vehicule = fields.Selection([
        ('voiture', 'Voiture'),
        ('moto', 'Moto (> 50cc)'),
        ('cyclomoteur', 'Cyclomoteur (< 50cc)'),
        ('velo', 'Vélo / VAE'),
    ], string='Type de véhicule', default='voiture', required=True)
    
    date_mise_circulation = fields.Date(string='Date de 1ère mise en circulation')
    
    active = fields.Boolean(default=True)
    
    trajet_ids = fields.One2many(
        'km.trajet',
        'vehicule_personnel_id',
        string='Trajets',
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
    )

    immatriculation_unique = models.Constraint(
        'UNIQUE(immatriculation, company_id)',
        "Cette immatriculation existe déjà!",
    )

    def action_voir_trajets(self):
        """Ouvre la liste des trajets pour ce véhicule personnel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Trajets - {self.name}',
            'res_model': 'km.trajet',
            'view_mode': 'list,form,calendar',
            'domain': [('vehicule_personnel_id', '=', self.id)],
            'context': {'default_vehicule_personnel_id': self.id},
        }
