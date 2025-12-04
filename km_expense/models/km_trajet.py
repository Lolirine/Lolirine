# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date


class KmTrajet(models.Model):
    """Trajet professionnel pour le calcul des indemnités kilométriques"""
    _name = 'km.trajet'
    _description = 'Trajet Professionnel'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Référence',
        readonly=True,
        copy=False,
        default='Nouveau',
    )
    
    # Informations de base
    date = fields.Date(
        string='Date du trajet',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    
    # Véhicule (soit du parc, soit personnel)
    type_vehicule_utilise = fields.Selection([
        ('parc', 'Véhicule de société'),
        ('personnel', 'Véhicule personnel'),
    ], string='Type de véhicule', default='personnel', required=True)
    
    vehicule_id = fields.Many2one(
        'fleet.vehicle',
        string='Véhicule de société',
    )
    
    vehicule_personnel_id = fields.Many2one(
        'km.vehicule.personnel',
        string='Véhicule personnel',
    )
    
    # Points de trajet
    lieu_depart = fields.Char(
        string='Lieu de départ',
        required=True,
        tracking=True,
    )
    lieu_arrivee = fields.Char(
        string='Lieu d\'arrivée',
        required=True,
        tracking=True,
    )
    
    # Trajet aller-retour
    aller_retour = fields.Boolean(
        string='Aller-retour',
        default=True,
        help="Cocher si le trajet est un aller-retour",
    )
    
    # Distance
    distance_aller = fields.Float(
        string='Distance aller (km)',
        required=True,
        digits=(10, 1),
    )
    distance = fields.Float(
        string='Distance totale (km)',
        compute='_compute_distance',
        store=True,
        digits=(10, 1),
    )
    
    # Catégorie et motif
    categorie_id = fields.Many2one(
        'km.trajet.categorie',
        string='Catégorie',
        required=True,
    )
    motif = fields.Text(
        string='Motif du déplacement',
        required=True,
        tracking=True,
    )
    
    # Client/Fournisseur associé
    partner_id = fields.Many2one(
        'res.partner',
        string='Client/Fournisseur',
        help="Client ou fournisseur visité lors de ce trajet",
    )
    
    # Calcul de l'indemnité
    puissance_fiscale = fields.Selection([
        ('3', '3 CV et moins'),
        ('4', '4 CV'),
        ('5', '5 CV'),
        ('6', '6 CV'),
        ('7', '7 CV et plus'),
    ], string='Puissance Fiscale',
       compute='_compute_puissance_fiscale',
       store=True,
       readonly=False,
    )
    
    type_vehicule_km = fields.Selection([
        ('voiture', 'Voiture'),
        ('moto', 'Moto (> 50cc)'),
        ('cyclomoteur', 'Cyclomoteur (< 50cc)'),
        ('velo', 'Vélo / VAE'),
    ], string='Type véhicule IK',
       compute='_compute_puissance_fiscale',
       store=True,
       readonly=False,
    )
    
    bareme_id = fields.Many2one(
        'km.bareme',
        string='Barème appliqué',
        compute='_compute_bareme',
        store=True,
    )
    
    taux_km = fields.Float(
        string='Taux (€/km)',
        compute='_compute_montant_indemnite',
        store=True,
        digits=(10, 4),
    )
    
    montant_indemnite = fields.Float(
        string='Montant Indemnité (€)',
        compute='_compute_montant_indemnite',
        store=True,
        digits=(10, 2),
        tracking=True,
    )
    
    # Statut
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('soumis', 'Soumis'),
        ('valide', 'Validé'),
        ('refuse', 'Refusé'),
        ('rembourse', 'Remboursé'),
    ], string='Statut', default='brouillon', tracking=True)
    
    # Lien avec les notes de frais
    expense_id = fields.Many2one(
        'hr.expense',
        string='Note de frais',
        readonly=True,
        copy=False,
    )
    
    # Champs techniques
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Devise',
    )
    
    notes = fields.Text(string='Notes internes')
    
    # Pièces jointes
    justificatif_ids = fields.Many2many(
        'ir.attachment',
        string='Justificatifs',
        help="Tickets de péage, parking, etc.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('km.trajet') or 'Nouveau'
        return super().create(vals_list)

    @api.depends('distance_aller', 'aller_retour')
    def _compute_distance(self):
        for trajet in self:
            if trajet.aller_retour:
                trajet.distance = trajet.distance_aller * 2
            else:
                trajet.distance = trajet.distance_aller

    @api.depends('type_vehicule_utilise', 'vehicule_id', 'vehicule_personnel_id')
    def _compute_puissance_fiscale(self):
        for trajet in self:
            if trajet.type_vehicule_utilise == 'parc' and trajet.vehicule_id:
                trajet.puissance_fiscale = trajet.vehicule_id.puissance_fiscale
                trajet.type_vehicule_km = trajet.vehicule_id.type_vehicule_km or 'voiture'
            elif trajet.type_vehicule_utilise == 'personnel' and trajet.vehicule_personnel_id:
                trajet.puissance_fiscale = trajet.vehicule_personnel_id.puissance_fiscale
                trajet.type_vehicule_km = trajet.vehicule_personnel_id.type_vehicule or 'voiture'

    @api.depends('date', 'puissance_fiscale', 'type_vehicule_km')
    def _compute_bareme(self):
        Bareme = self.env['km.bareme']
        for trajet in self:
            if trajet.date and trajet.puissance_fiscale:
                trajet.bareme_id = Bareme.get_bareme_applicable(
                    trajet.date,
                    trajet.puissance_fiscale,
                    trajet.type_vehicule_km or 'voiture',
                )
            else:
                trajet.bareme_id = False

    @api.depends('distance', 'bareme_id', 'employee_id', 'date')
    def _compute_montant_indemnite(self):
        for trajet in self:
            if not trajet.bareme_id or trajet.distance <= 0:
                trajet.taux_km = 0.0
                trajet.montant_indemnite = 0.0
                continue
            
            # Calcul du cumul annuel pour cet employé
            debut_annee = date(trajet.date.year, 1, 1)
            trajets_annee = self.search([
                ('employee_id', '=', trajet.employee_id.id),
                ('date', '>=', debut_annee),
                ('date', '<', trajet.date),
                ('state', 'in', ('valide', 'rembourse')),
            ])
            cumul_km = sum(trajets_annee.mapped('distance'))
            
            # Calcul avec le cumul
            total_avec_trajet = cumul_km + trajet.distance
            montant_total = trajet.bareme_id.calculer_indemnite(total_avec_trajet)
            montant_cumul = trajet.bareme_id.calculer_indemnite(cumul_km)
            
            trajet.montant_indemnite = montant_total - montant_cumul
            trajet.taux_km = trajet.montant_indemnite / trajet.distance if trajet.distance else 0.0

    @api.onchange('type_vehicule_utilise')
    def _onchange_type_vehicule(self):
        if self.type_vehicule_utilise == 'parc':
            self.vehicule_personnel_id = False
        else:
            self.vehicule_id = False

    @api.constrains('distance_aller')
    def _check_distance(self):
        for trajet in self:
            if trajet.distance_aller <= 0:
                raise ValidationError("La distance doit être supérieure à 0.")

    def action_soumettre(self):
        """Soumettre le trajet pour validation"""
        for trajet in self:
            if trajet.state != 'brouillon':
                raise UserError("Seuls les trajets en brouillon peuvent être soumis.")
            trajet.state = 'soumis'

    def action_valider(self):
        """Valider le trajet"""
        for trajet in self:
            if trajet.state != 'soumis':
                raise UserError("Seuls les trajets soumis peuvent être validés.")
            trajet.state = 'valide'

    def action_refuser(self):
        """Refuser le trajet"""
        for trajet in self:
            if trajet.state != 'soumis':
                raise UserError("Seuls les trajets soumis peuvent être refusés.")
            trajet.state = 'refuse'

    def action_remettre_brouillon(self):
        """Remettre en brouillon"""
        for trajet in self:
            if trajet.state in ('rembourse',):
                raise UserError("Un trajet remboursé ne peut pas être remis en brouillon.")
            trajet.state = 'brouillon'

    def action_creer_note_frais(self):
        """Créer une note de frais à partir du trajet"""
        self.ensure_one()
        if self.state != 'valide':
            raise UserError("Le trajet doit être validé avant de créer une note de frais.")
        if self.expense_id:
            raise UserError("Une note de frais existe déjà pour ce trajet.")
        
        # Recherche du produit pour les indemnités kilométriques
        product = self.env.ref('km_expense.product_indemnite_km', raise_if_not_found=False)
        if not product:
            product = self.env['product.product'].search([
                ('can_be_expensed', '=', True),
                ('default_code', '=', 'IK'),
            ], limit=1)
        
        if not product:
            raise UserError(
                "Veuillez configurer un produit pour les indemnités kilométriques."
            )
        
        expense_vals = {
            'name': f"IK - {self.name} - {self.lieu_depart} → {self.lieu_arrivee}",
            'employee_id': self.employee_id.id,
            'product_id': product.id,
            'quantity': self.distance,
            'unit_amount': self.taux_km,
            'total_amount': self.montant_indemnite,
            'date': self.date,
            'description': f"Trajet: {self.lieu_depart} → {self.lieu_arrivee}\n"
                          f"Motif: {self.motif}\n"
                          f"Distance: {self.distance} km",
        }
        
        expense = self.env['hr.expense'].create(expense_vals)
        self.expense_id = expense
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Note de frais',
            'res_model': 'hr.expense',
            'res_id': expense.id,
            'view_mode': 'form',
        }

    def action_voir_note_frais(self):
        """Ouvrir la note de frais associée"""
        self.ensure_one()
        if not self.expense_id:
            raise UserError("Aucune note de frais associée à ce trajet.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Note de frais',
            'res_model': 'hr.expense',
            'res_id': self.expense_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class KmTrajetCategorie(models.Model):
    """Catégories de trajets"""
    _name = 'km.trajet.categorie'
    _description = 'Catégorie de Trajet'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Séquence', default=10)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Couleur')
    
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, company_id)', 'Le code doit être unique!')
    ]
