# -*- coding: utf-8 -*-

import logging
import requests
import io
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# URL fichier Excel Statbel pour l'indice santé belge
STATBEL_XLSX_URL = "https://statbel.fgov.be/sites/default/files/files/opendata/Consumptieprijsindex%20en%20gezondheidsindex/CPI%20All%20base%20years.xlsx"


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
        Récupère l'indice santé belge depuis le fichier Excel Statbel.
        Retourne le dernier indice disponible si year/month non spécifiés.
        """
        try:
            _logger.info("Récupération de l'indice santé depuis Statbel (XLSX)...")
            
            # Télécharger le fichier Excel
            response = requests.get(STATBEL_XLSX_URL, timeout=60)
            response.raise_for_status()
            
            # Parser le fichier Excel avec openpyxl
            try:
                import openpyxl
            except ImportError:
                raise UserError(_(
                    "Le module 'openpyxl' est requis pour lire les fichiers Excel. "
                    "Veuillez l'installer avec: pip install openpyxl"
                ))
            
            # Charger le workbook depuis le contenu téléchargé
            wb = openpyxl.load_workbook(io.BytesIO(response.content), data_only=True)
            
            # Chercher la feuille contenant "Health" ou "Santé" ou prendre la première
            sheet = None
            for sheet_name in wb.sheetnames:
                if 'health' in sheet_name.lower() or 'santé' in sheet_name.lower() or 'gezondheid' in sheet_name.lower():
                    sheet = wb[sheet_name]
                    break
            
            if not sheet:
                sheet = wb.active
            
            _logger.info(f"Lecture de la feuille: {sheet.title}")
            
            # Trouver les colonnes pertinentes
            # Structure typique: Année, Mois, Indice santé (base 2013=100), etc.
            header_row = 1
            year_col = None
            month_col = None
            health_index_col = None
            
            # Parcourir la première ligne pour trouver les en-têtes
            for col in range(1, sheet.max_column + 1):
                cell_value = str(sheet.cell(row=header_row, column=col).value or '').lower()
                if 'year' in cell_value or 'année' in cell_value or 'jaar' in cell_value:
                    year_col = col
                elif 'month' in cell_value or 'mois' in cell_value or 'maand' in cell_value:
                    month_col = col
                elif ('health' in cell_value or 'santé' in cell_value or 'gezondheid' in cell_value) and ('2013' in cell_value or 'index' in cell_value):
                    health_index_col = col
            
            # Si colonnes non trouvées, essayer avec des indices fixes
            if not all([year_col, month_col, health_index_col]):
                _logger.warning("En-têtes non trouvés, utilisation des colonnes par défaut")
                year_col = 1
                month_col = 2
                # Chercher la colonne avec "2013" (base de l'indice santé actuel)
                for col in range(1, min(sheet.max_column + 1, 20)):
                    cell_value = str(sheet.cell(row=header_row, column=col).value or '')
                    if '2013' in cell_value and ('health' in cell_value.lower() or 'santé' in cell_value.lower() or 'gezondheid' in cell_value.lower()):
                        health_index_col = col
                        break
                if not health_index_col:
                    health_index_col = 4  # Colonne par défaut

            _logger.info(f"Colonnes trouvées - Année: {year_col}, Mois: {month_col}, Indice: {health_index_col}")
            
            # Lire les données
            indices = []
            for row in range(2, sheet.max_row + 1):
                row_year = sheet.cell(row=row, column=year_col).value
                row_month = sheet.cell(row=row, column=month_col).value
                row_value = sheet.cell(row=row, column=health_index_col).value
                
                if row_year and row_month and row_value:
                    try:
                        indices.append({
                            'year': int(row_year),
                            'month': int(row_month),
                            'value': float(row_value)
                        })
                    except (ValueError, TypeError):
                        continue
            
            wb.close()
            
            if not indices:
                raise UserError(_("Aucun indice trouvé dans le fichier Statbel"))
            
            # Trier par date décroissante
            indices.sort(key=lambda x: (x['year'], x['month']), reverse=True)
            
            # Filtrer par année/mois si spécifié
            if year and month:
                for idx in indices:
                    if idx['year'] == int(year) and idx['month'] == int(month):
                        return {
                            'value': idx['value'],
                            'date': date(idx['year'], idx['month'], 1),
                            'source': 'statbel'
                        }
                raise UserError(_(
                    "Indice non trouvé pour %s/%s. "
                    "Dernier indice disponible: %s/%s"
                ) % (month, year, indices[0]['month'], indices[0]['year']))
            
            # Retourner le plus récent
            latest = indices[0]
            return {
                'value': latest['value'],
                'date': date(latest['year'], latest['month'], 1),
                'source': 'statbel'
            }
            
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
