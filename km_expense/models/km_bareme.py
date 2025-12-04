# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class KmBareme(models.Model):
    """Barème kilométrique pour le calcul des indemnités"""
    _name = 'km.bareme'
    _description = 'Barème Kilométrique'
    _order = 'date_debut desc, puissance_fiscale'

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
    )
    puissance_fiscale = fields.Selection([
        ('3', '3 CV et moins'),
        ('4', '4 CV'),
        ('5', '5 CV'),
        ('6', '6 CV'),
        ('7', '7 CV et plus'),
    ], string='Puissance Fiscale', required=True)
    
    # Tranches de distance
    taux_jusqu_5000 = fields.Float(
        string="Taux jusqu'à 5000 km (€/km)",
        digits=(10, 4),
        required=True,
        help="Taux par kilomètre pour la tranche 0-5000 km",
    )
    taux_5001_20000 = fields.Float(
        string='Taux 5001-20000 km (€/km)',
        digits=(10, 4),
        required=True,
        help="Taux par kilomètre pour la tranche 5001-20000 km",
    )
    majoration_5001_20000 = fields.Float(
        string='Majoration 5001-20000 km (€)',
        digits=(10, 2),
        default=0.0,
        help="Montant fixe à ajouter pour la tranche 5001-20000 km",
    )
    taux_au_dela_20000 = fields.Float(
        string='Taux au-delà de 20000 km (€/km)',
        digits=(10, 4),
        required=True,
        help="Taux par kilomètre au-delà de 20000 km",
    )
    
    date_debut = fields.Date(
        string='Date de début',
        required=True,
        help="Date de début de validité du barème",
    )
    date_fin = fields.Date(
        string='Date de fin',
        help="Date de fin de validité du barème (laisser vide si toujours valide)",
    )
    
    type_vehicule = fields.Selection([
        ('voiture', 'Voiture'),
        ('moto', 'Moto (> 50cc)'),
        ('cyclomoteur', 'Cyclomoteur (< 50cc)'),
        ('velo', 'Vélo / VAE'),
    ], string='Type de véhicule', default='voiture', required=True)
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company,
    )
    notes = fields.Text(string='Notes')

    @api.depends('puissance_fiscale', 'date_debut', 'type_vehicule')
    def _compute_name(self):
        puissance_labels = dict(self._fields['puissance_fiscale'].selection)
        type_labels = dict(self._fields['type_vehicule'].selection)
        for record in self:
            puissance = puissance_labels.get(record.puissance_fiscale, '')
            type_veh = type_labels.get(record.type_vehicule, '')
            date = record.date_debut.strftime('%Y') if record.date_debut else ''
            record.name = f"{type_veh} - {puissance} - {date}"

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for record in self:
            if record.date_fin and record.date_debut > record.date_fin:
                raise ValidationError(
                    "La date de fin doit être postérieure à la date de début."
                )

    def calculer_indemnite(self, distance_totale):
        """
        Calcule l'indemnité kilométrique selon le barème
        
        :param distance_totale: Distance totale en kilomètres
        :return: Montant de l'indemnité en euros
        """
        self.ensure_one()
        
        if distance_totale <= 0:
            return 0.0
        
        if distance_totale <= 5000:
            return distance_totale * self.taux_jusqu_5000
        elif distance_totale <= 20000:
            return (distance_totale * self.taux_5001_20000) + self.majoration_5001_20000
        else:
            return distance_totale * self.taux_au_dela_20000

    @api.model
    def get_bareme_applicable(self, date, puissance_fiscale, type_vehicule='voiture'):
        """
        Récupère le barème applicable pour une date et puissance fiscale données
        """
        domain = [
            ('puissance_fiscale', '=', puissance_fiscale),
            ('type_vehicule', '=', type_vehicule),
            ('date_debut', '<=', date),
            '|',
            ('date_fin', '=', False),
            ('date_fin', '>=', date),
        ]
        return self.search(domain, limit=1, order='date_debut desc')
