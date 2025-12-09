# -*- coding: utf-8 -*-

import logging
import requests
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# URL API Statbel pour l'indice santé belge
STATBEL_API_URL = "https://statbel.fgov.be/sites/default/files/files/opendata/Consumptieprijsindex/CPI%20All%20groups_month.json"


class StoragePriceIndex(models.Model):
    """Modèle pour stocker les indices de prix (indice santé, CPI, etc.)"""
    _name = 'storage.price.index'
    _description = 'Indice de prix pour indexation'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Référence',
        required=True,
        tracking=True,
        help="Référence unique de l'indice (ex: 2024-01)"
    )
    index_type = fields.Selection([
        ('health', 'Indice Santé Belge'),
        ('cpi', 'Indice des Prix à la Consommation (CPI)'),
        ('custom', 'Indice Personnalisé'),
    ], string='Type d\'indice', required=True, default='health', tracking=True)
    
    date = fields.Date(
        string='Date',
        required=True,
        tracking=True,
        help="Date de référence de l'indice (généralement le 1er du mois)"
    )
    year = fields.Integer(
        string='Année',
        compute='_compute_year_month',
        store=True
    )
    month = fields.Integer(
        string='Mois',
        compute='_compute_year_month',
        store=True
    )
    
    value = fields.Float(
        string='Valeur de l\'indice',
        required=True,
        digits=(10, 2),
        tracking=True,
        help="Valeur numérique de l'indice"
    )
    base_year = fields.Integer(
        string='Année de base',
        default=2013,
        help="Année de référence pour le calcul de l'indice (base 100)"
    )
    
    source = fields.Selection([
        ('statbel', 'Statbel (automatique)'),
        ('manual', 'Saisie manuelle'),
        ('import', 'Import fichier'),
    ], string='Source', default='manual', tracking=True)
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company
    )
    
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_index_date_type', 
         'UNIQUE(date, index_type, company_id)', 
         'Un seul indice par date et type est autorisé par société!')
    ]

    @api.depends('date')
    def _compute_year_month(self):
        for record in self:
            if record.date:
                record.year = record.date.year
                record.month = record.date.month
            else:
                record.year = 0
                record.month = 0

    @api.model
    def _fetch_statbel_health_index(self, year=None, month=None):
        """
        Récupère l'indice santé belge depuis l'API Statbel.
        Retourne le dernier indice disponible si year/month non spécifiés.
        """
        try:
            _logger.info("Récupération de l'indice santé depuis Statbel...")
            
            response = requests.get(STATBEL_API_URL, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # L'API retourne une liste d'indices par mois
            # On filtre pour obtenir l'indice santé (Health Index)
            health_indices = []
            
            for item in data:
                # Adapter selon la structure réelle de l'API Statbel
                if 'health_index' in str(item).lower() or item.get('type') == 'health':
                    health_indices.append(item)
            
            if not health_indices:
                # Si pas de filtre spécifique, prendre le dernier élément
                health_indices = data if isinstance(data, list) else [data]
            
            # Trier par date décroissante et prendre le plus récent
            # ou filtrer par année/mois si spécifié
            if year and month:
                for idx in health_indices:
                    idx_year = idx.get('year') or idx.get('periode', '').split('-')[0]
                    idx_month = idx.get('month') or idx.get('periode', '').split('-')[1] if '-' in str(idx.get('periode', '')) else None
                    if str(idx_year) == str(year) and str(idx_month) == str(month):
                        return {
                            'value': float(idx.get('value', idx.get('index', 0))),
                            'date': date(int(year), int(month), 1),
                            'source': 'statbel'
                        }
            
            # Sinon retourner le plus récent
            if health_indices:
                latest = health_indices[-1]
                return {
                    'value': float(latest.get('value', latest.get('index', 0))),
                    'date': date.today().replace(day=1),
                    'source': 'statbel'
                }
            
            return None
            
        except requests.RequestException as e:
            _logger.error(f"Erreur lors de la récupération de l'indice Statbel: {e}")
            raise UserError(_(
                "Impossible de récupérer l'indice depuis Statbel. "
                "Veuillez réessayer plus tard ou saisir l'indice manuellement.\n\n"
                "Erreur technique: %s"
            ) % str(e))
        except Exception as e:
            _logger.error(f"Erreur inattendue: {e}")
            raise UserError(_("Erreur inattendue: %s") % str(e))

    @api.model
    def fetch_latest_health_index(self):
        """Action pour récupérer et enregistrer le dernier indice santé"""
        result = self._fetch_statbel_health_index()
        
        if result:
            # Vérifier si l'indice existe déjà
            existing = self.search([
                ('date', '=', result['date']),
                ('index_type', '=', 'health'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if existing:
                existing.write({
                    'value': result['value'],
                    'source': 'statbel'
                })
                return existing
            
            # Créer nouvel indice
            return self.create({
                'name': f"Indice Santé {result['date'].strftime('%Y-%m')}",
                'index_type': 'health',
                'date': result['date'],
                'value': result['value'],
                'source': 'statbel',
                'base_year': 2013,
            })
        
        return False

    @api.model
    def get_index_for_date(self, target_date, index_type='health'):
        """
        Récupère l'indice pour une date donnée.
        Si pas d'indice exact, retourne le plus proche précédent.
        """
        domain = [
            ('index_type', '=', index_type),
            ('date', '<=', target_date),
            ('company_id', '=', self.env.company.id)
        ]
        return self.search(domain, order='date desc', limit=1)

    @api.model
    def get_base_index(self, contract_date, index_type='health'):
        """
        Récupère l'indice de base pour un contrat (date de signature).
        """
        return self.get_index_for_date(contract_date, index_type)

    @api.model
    def get_current_index(self, index_type='health'):
        """Récupère l'indice le plus récent"""
        return self.get_index_for_date(date.today(), index_type)

    def action_fetch_from_statbel(self):
        """Bouton pour récupérer l'indice depuis Statbel"""
        self.ensure_one()
        if self.index_type != 'health':
            raise UserError(_("Seul l'indice santé peut être récupéré depuis Statbel"))
        
        result = self._fetch_statbel_health_index(self.year, self.month)
        if result:
            self.write({
                'value': result['value'],
                'source': 'statbel'
            })
        return True

    @api.model
    def _cron_fetch_health_index(self):
        """
        CRON job pour récupérer automatiquement l'indice santé chaque mois.
        Exécuté le 5 de chaque mois.
        """
        _logger.info("CRON: Récupération automatique de l'indice santé...")
        
        companies = self.env['res.company'].search([])
        for company in companies:
            try:
                self.with_company(company).fetch_latest_health_index()
                _logger.info(f"Indice santé mis à jour pour {company.name}")
            except Exception as e:
                _logger.error(f"Erreur mise à jour indice pour {company.name}: {e}")
        
        return True
