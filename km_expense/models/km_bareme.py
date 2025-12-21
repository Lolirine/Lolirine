# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta


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
    
    # Gestion trimestrielle
    trimestre = fields.Selection([
        ('T1', 'T1 (Janvier - Mars)'),
        ('T2', 'T2 (Avril - Juin)'),
        ('T3', 'T3 (Juillet - Septembre)'),
        ('T4', 'T4 (Octobre - Décembre)'),
    ], string='Trimestre', compute='_compute_trimestre', store=True)
    
    annee = fields.Char(
        string='Année',
        compute='_compute_trimestre',
        store=True,
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
    
    # Source officielle du taux
    source_officielle = fields.Char(
        string='Source',
        help="Référence officielle (ex: AR du 01/07/2024)",
    )

    @api.depends('date_debut')
    def _compute_trimestre(self):
        for record in self:
            if record.date_debut:
                month = record.date_debut.month
                record.annee = str(record.date_debut.year)
                if month in [1, 2, 3]:
                    record.trimestre = 'T1'
                elif month in [4, 5, 6]:
                    record.trimestre = 'T2'
                elif month in [7, 8, 9]:
                    record.trimestre = 'T3'
                else:
                    record.trimestre = 'T4'
            else:
                record.trimestre = False
                record.annee = False

    @api.depends('puissance_fiscale', 'date_debut', 'type_vehicule', 'trimestre', 'annee')
    def _compute_name(self):
        puissance_labels = dict(self._fields['puissance_fiscale'].selection)
        type_labels = dict(self._fields['type_vehicule'].selection)
        for record in self:
            puissance = puissance_labels.get(record.puissance_fiscale, '')
            type_veh = type_labels.get(record.type_vehicule, '')
            periode = f"{record.trimestre} {record.annee}" if record.trimestre and record.annee else ''
            record.name = f"{type_veh} - {puissance} - {periode}"

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
    def get_bareme_applicable(self, date_trajet, puissance_fiscale, type_vehicule='voiture'):
        """
        Récupère le barème applicable pour une date et puissance fiscale données.
        Si aucun barème n'est trouvé pour cette date, retourne le dernier barème connu.
        """
        # Chercher un barème exactement applicable à la date
        domain = [
            ('puissance_fiscale', '=', puissance_fiscale),
            ('type_vehicule', '=', type_vehicule),
            ('date_debut', '<=', date_trajet),
            '|',
            ('date_fin', '=', False),
            ('date_fin', '>=', date_trajet),
        ]
        bareme = self.search(domain, limit=1, order='date_debut desc')
        
        # Si aucun barème trouvé, utiliser le dernier barème connu (fallback)
        if not bareme:
            # Chercher le barème le plus récent pour cette puissance/type
            domain_fallback = [
                ('puissance_fiscale', '=', puissance_fiscale),
                ('type_vehicule', '=', type_vehicule),
            ]
            bareme = self.search(domain_fallback, limit=1, order='date_fin desc, date_debut desc')
        
        return bareme

    @api.model
    def get_trimestre_info(self, date_ref=None):
        """
        Retourne les informations sur le trimestre actuel et suivant
        """
        if not date_ref:
            date_ref = date.today()
        
        # Déterminer le trimestre actuel
        month = date_ref.month
        year = date_ref.year
        
        if month in [1, 2, 3]:
            trimestre_actuel = 'T1'
            debut_trimestre = date(year, 1, 1)
            fin_trimestre = date(year, 3, 31)
            trimestre_suivant = 'T2'
            debut_suivant = date(year, 4, 1)
        elif month in [4, 5, 6]:
            trimestre_actuel = 'T2'
            debut_trimestre = date(year, 4, 1)
            fin_trimestre = date(year, 6, 30)
            trimestre_suivant = 'T3'
            debut_suivant = date(year, 7, 1)
        elif month in [7, 8, 9]:
            trimestre_actuel = 'T3'
            debut_trimestre = date(year, 7, 1)
            fin_trimestre = date(year, 9, 30)
            trimestre_suivant = 'T4'
            debut_suivant = date(year, 10, 1)
        else:
            trimestre_actuel = 'T4'
            debut_trimestre = date(year, 10, 1)
            fin_trimestre = date(year, 12, 31)
            trimestre_suivant = 'T1'
            debut_suivant = date(year + 1, 1, 1)
        
        jours_restants = (fin_trimestre - date_ref).days
        
        return {
            'trimestre_actuel': trimestre_actuel,
            'annee_actuelle': year,
            'debut_trimestre': debut_trimestre,
            'fin_trimestre': fin_trimestre,
            'jours_restants': jours_restants,
            'trimestre_suivant': trimestre_suivant,
            'debut_suivant': debut_suivant,
            'annee_suivante': debut_suivant.year,
        }

    @api.model
    def get_bareme_trimestre_suivant(self, puissance_fiscale='7', type_vehicule='voiture'):
        """
        Récupère le barème du trimestre suivant s'il existe
        """
        info = self.get_trimestre_info()
        
        domain = [
            ('puissance_fiscale', '=', puissance_fiscale),
            ('type_vehicule', '=', type_vehicule),
            ('date_debut', '>=', info['debut_suivant']),
        ]
        return self.search(domain, limit=1, order='date_debut asc')

    @api.model
    def check_alerte_changement_trimestre(self):
        """
        Vérifie s'il y a une alerte à afficher concernant le changement de trimestre.
        Appelé par le cron ou à l'affichage.
        Retourne un dict avec les infos d'alerte si nécessaire.
        """
        info = self.get_trimestre_info()
        
        # Alerte si moins de 15 jours avant la fin du trimestre
        if info['jours_restants'] <= 15:
            # Vérifier si le barème du trimestre suivant existe
            bareme_suivant = self.get_bareme_trimestre_suivant()
            
            if bareme_suivant:
                # Comparer avec le barème actuel
                bareme_actuel = self.search([
                    ('puissance_fiscale', '=', '7'),
                    ('type_vehicule', '=', 'voiture'),
                    ('date_debut', '<=', date.today()),
                    '|',
                    ('date_fin', '=', False),
                    ('date_fin', '>=', date.today()),
                ], limit=1, order='date_debut desc')
                
                if bareme_actuel and bareme_actuel.taux_jusqu_5000 != bareme_suivant.taux_jusqu_5000:
                    return {
                        'type': 'changement',
                        'message': f"⚠️ Changement de taux le {info['debut_suivant'].strftime('%d/%m/%Y')} ! "
                                   f"Taux actuel: {bareme_actuel.taux_jusqu_5000:.4f} €/km → "
                                   f"Nouveau taux: {bareme_suivant.taux_jusqu_5000:.4f} €/km",
                        'jours_restants': info['jours_restants'],
                        'taux_actuel': bareme_actuel.taux_jusqu_5000,
                        'taux_suivant': bareme_suivant.taux_jusqu_5000,
                    }
                else:
                    return {
                        'type': 'info',
                        'message': f"ℹ️ Le barème {info['trimestre_suivant']} {info['annee_suivante']} est configuré.",
                        'jours_restants': info['jours_restants'],
                    }
            else:
                return {
                    'type': 'warning',
                    'message': f"⚠️ Attention ! Le barème {info['trimestre_suivant']} {info['annee_suivante']} "
                               f"n'est pas encore configuré. Fin du trimestre actuel dans {info['jours_restants']} jours.",
                    'jours_restants': info['jours_restants'],
                    'trimestre_suivant': f"{info['trimestre_suivant']} {info['annee_suivante']}",
                }
        
        return None

    @api.model
    def action_creer_bareme_trimestre_suivant(self):
        """
        Action pour créer les barèmes du trimestre suivant en copiant les actuels
        """
        info = self.get_trimestre_info()
        
        # Récupérer les barèmes du trimestre actuel
        baremes_actuels = self.search([
            ('date_debut', '>=', info['debut_trimestre']),
            ('date_debut', '<=', info['fin_trimestre']),
        ])
        
        if not baremes_actuels:
            # Prendre les barèmes actifs
            baremes_actuels = self.search([('active', '=', True)])
        
        created = self.env['km.bareme']
        for bareme in baremes_actuels:
            # Vérifier si le barème suivant existe déjà
            existing = self.search([
                ('puissance_fiscale', '=', bareme.puissance_fiscale),
                ('type_vehicule', '=', bareme.type_vehicule),
                ('date_debut', '=', info['debut_suivant']),
            ], limit=1)
            
            if not existing:
                new_bareme = bareme.copy({
                    'date_debut': info['debut_suivant'],
                    'date_fin': False,
                    'notes': f"Copié depuis {bareme.name} - À METTRE À JOUR avec le nouveau taux officiel",
                })
                created |= new_bareme
                
                # Mettre à jour la date de fin de l'ancien barème
                if not bareme.date_fin:
                    bareme.date_fin = info['fin_trimestre']
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Barèmes créés',
                'message': f'{len(created)} barème(s) créé(s) pour {info["trimestre_suivant"]} {info["annee_suivante"]}. '
                           f'Pensez à mettre à jour les taux avec les valeurs officielles !',
                'type': 'warning' if created else 'info',
                'sticky': True,
            }
        }

    @api.model
    def cron_check_trimestre_alert(self):
        """
        Méthode appelée par le cron pour vérifier et envoyer des alertes
        sur le changement de trimestre
        """
        alerte = self.check_alerte_changement_trimestre()
        
        if alerte and alerte['type'] == 'warning':
            # Envoyer une notification aux managers IK
            managers = self.env.ref('km_expense.group_km_expense_manager').users
            
            for user in managers:
                # Créer une activité pour rappeler de configurer les barèmes
                self.env['mail.activity'].create({
                    'res_model_id': self.env.ref('km_expense.model_km_bareme').id,
                    'res_id': self.search([], limit=1).id or 1,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': f"Configurer barèmes {alerte.get('trimestre_suivant', 'prochain trimestre')}",
                    'note': alerte['message'],
                    'user_id': user.id,
                    'date_deadline': date.today() + timedelta(days=alerte['jours_restants']),
                })
        
        return True
