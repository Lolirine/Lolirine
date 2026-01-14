# -*- coding: utf-8 -*-
"""
Extension of res.company for Belgian fiscal data required by Biztax
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class ResCompany(models.Model):
    _inherit = 'res.company'

    # =========================================================================
    # BELGIAN FISCAL IDENTIFICATION
    # =========================================================================
    
    bce_number = fields.Char(
        string="Numéro BCE/KBO",
        size=14,
        help="Numéro d'entreprise belge au format 0XXX.XXX.XXX",
        tracking=True,
    )
    
    tax_identification_number = fields.Char(
        string="Numéro d'identification fiscale",
        help="Numéro d'identification fiscale si différent du BCE",
        tracking=True,
    )
    
    nace_code = fields.Char(
        string="Code NACE",
        size=10,
        help="Code d'activité économique NACE-BEL (ex: 68.100)",
        tracking=True,
    )
    
    # =========================================================================
    # LEGAL FORM
    # =========================================================================
    
    legal_form = fields.Selection([
        ('sa', 'SA - Société Anonyme'),
        ('srl', 'SRL - Société à Responsabilité Limitée'),
        ('sc', 'SC - Société Coopérative'),
        ('scrl', 'SCRL - Société Coopérative à Responsabilité Limitée'),
        ('snc', 'SNC - Société en Nom Collectif'),
        ('scs', 'SCS - Société en Commandite Simple'),
        ('sca', 'SCA - Société en Commandite par Actions'),
        ('se', 'SE - Société Européenne'),
        ('asbl', 'ASBL - Association Sans But Lucratif'),
        ('aisbl', 'AISBL - Association Internationale Sans But Lucratif'),
        ('fondation', 'Fondation'),
        ('gie', 'GIE - Groupement d\'Intérêt Économique'),
        ('ei', 'EI - Entreprise Individuelle'),
        ('other', 'Autre'),
    ], string="Forme juridique", default='srl', tracking=True)
    
    legal_form_code = fields.Char(
        string="Code forme juridique",
        compute='_compute_legal_form_code',
        store=True,
        help="Code officiel pour la taxonomie be-tax",
    )
    
    accounting_standard = fields.Selection([
        ('full', 'Schéma complet'),
        ('abbreviated', 'Schéma abrégé'),
        ('micro', 'Micro-schéma'),
    ], string="Schéma comptable", default='abbreviated',
       help="Schéma de comptes annuels applicable", tracking=True)
    
    # =========================================================================
    # SME STATUS
    # =========================================================================
    
    is_sme = fields.Boolean(
        string="PME",
        help="L'entreprise est-elle une PME au sens de l'article 1:24 CSA? "
             "Donne droit au taux réduit de 20% sur les premiers 100.000€",
        tracking=True,
    )
    
    # =========================================================================
    # FISCAL YEAR CONFIGURATION
    # =========================================================================
    
    fiscal_year_start_day = fields.Integer(
        string="Jour de début d'exercice",
        default=1,
    )
    
    fiscal_year_start_month = fields.Selection([
        ('1', 'Janvier'),
        ('2', 'Février'),
        ('3', 'Mars'),
        ('4', 'Avril'),
        ('5', 'Mai'),
        ('6', 'Juin'),
        ('7', 'Juillet'),
        ('8', 'Août'),
        ('9', 'Septembre'),
        ('10', 'Octobre'),
        ('11', 'Novembre'),
        ('12', 'Décembre'),
    ], string="Mois de début d'exercice", default='1')
    
    # =========================================================================
    # BIZTAX DEFAULT CONFIGURATION
    # =========================================================================
    
    biztax_default_taxonomy = fields.Selection([
        ('2024', 'Taxonomie 2024 (ex. imp. 2025)'),
        ('2023', 'Taxonomie 2023 (ex. imp. 2024)'),
        ('2022', 'Taxonomie 2022 (ex. imp. 2023)'),
    ], string="Taxonomie par défaut", default='2024')
    
    biztax_auto_adjustments = fields.Boolean(
        string="Ajustements automatiques",
        default=True,
        help="Générer automatiquement les ajustements fiscaux standards",
    )
    
    biztax_default_tax_rate = fields.Float(
        string="Taux ISOC standard (%)",
        default=25.0,
        help="Taux normal de l'impôt des sociétés",
    )
    
    biztax_sme_reduced_rate = fields.Float(
        string="Taux réduit PME (%)",
        default=20.0,
        help="Taux réduit pour les PME sur la première tranche",
    )
    
    biztax_sme_threshold = fields.Float(
        string="Seuil taux réduit (€)",
        default=100000.0,
        help="Montant jusqu'auquel le taux réduit s'applique",
    )
    
    # =========================================================================
    # ANNEXES CONFIGURATION
    # =========================================================================
    
    biztax_auto_generate_annexes = fields.Boolean(
        string="Générer annexes automatiquement",
        default=True,
        help="Générer automatiquement les annexes PDF obligatoires",
    )
    
    biztax_include_balance_sheet = fields.Boolean(
        string="Inclure bilan",
        default=True,
        help="Inclure automatiquement le bilan dans les annexes",
    )
    
    biztax_include_profit_loss = fields.Boolean(
        string="Inclure compte de résultat",
        default=True,
        help="Inclure automatiquement le compte de résultat dans les annexes",
    )
    
    # =========================================================================
    # REPRESENTATIVES
    # =========================================================================
    
    biztax_representative_id = fields.Many2one(
        'res.partner',
        string="Représentant légal",
        help="Personne autorisée à signer les déclarations fiscales",
        domain="[('is_company', '=', False)]",
    )
    
    biztax_accountant_id = fields.Many2one(
        'res.partner',
        string="Comptable/Expert-comptable",
        help="Comptable ou expert-comptable responsable",
    )
    
    biztax_accountant_itaa_number = fields.Char(
        string="Numéro ITAA",
        help="Numéro d'inscription à l'ITAA du comptable",
    )
    
    # =========================================================================
    # REGISTERED OFFICE (if different from main address)
    # =========================================================================
    
    biztax_use_different_registered_address = fields.Boolean(
        string="Siège social différent",
        help="Utiliser une adresse de siège social différente de l'adresse principale",
    )
    
    biztax_registered_street = fields.Char(string="Rue (siège)")
    biztax_registered_street2 = fields.Char(string="Rue 2")
    biztax_registered_zip = fields.Char(string="Code postal")
    biztax_registered_city = fields.Char(string="Ville")
    biztax_registered_country_id = fields.Many2one(
        'res.country',
        string="Pays",
        default=lambda self: self.env.ref('base.be', raise_if_not_found=False),
    )
    
    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================
    
    @api.depends('legal_form')
    def _compute_legal_form_code(self):
        """Map legal form to official be-tax code"""
        codes = {
            'sa': '014',
            'srl': '015',
            'sc': '016',
            'scrl': '016',
            'snc': '011',
            'scs': '012',
            'sca': '013',
            'se': '025',
            'asbl': '017',
            'aisbl': '018',
            'fondation': '019',
            'gie': '610',
            'ei': '001',
            'other': '099',
        }
        for company in self:
            company.legal_form_code = codes.get(company.legal_form, '099')
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def get_bce_number_clean(self):
        """Return BCE number without dots/spaces for XBRL"""
        self.ensure_one()
        number = self.bce_number or self.company_registry or ''
        return re.sub(r'[.\s-]', '', number)
    
    def get_bce_number_formatted(self):
        """Return BCE number in formatted display"""
        self.ensure_one()
        clean = self.get_bce_number_clean()
        if len(clean) == 10:
            return f"{clean[0:4]}.{clean[4:7]}.{clean[7:10]}"
        return clean
    
    def get_registered_address(self):
        """Return registered office address (or main address if not set)"""
        self.ensure_one()
        if self.biztax_use_different_registered_address and self.biztax_registered_street:
            return {
                'street': self.biztax_registered_street,
                'street2': self.biztax_registered_street2,
                'zip': self.biztax_registered_zip,
                'city': self.biztax_registered_city,
                'country_id': self.biztax_registered_country_id.id if self.biztax_registered_country_id else False,
                'country_code': self.biztax_registered_country_id.code if self.biztax_registered_country_id else 'BE',
            }
        return {
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'country_id': self.country_id.id if self.country_id else False,
            'country_code': self.country_id.code if self.country_id else 'BE',
        }
    
    def get_fiscal_year_dates(self, year):
        """
        Calculate fiscal year start and end dates for a given year.
        Returns tuple (start_date, end_date)
        """
        self.ensure_one()
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        start_month = int(self.fiscal_year_start_month or '1')
        start_day = self.fiscal_year_start_day or 1
        
        # Fiscal year start
        if start_month == 1 and start_day == 1:
            # Calendar year
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
        else:
            # Non-calendar fiscal year
            start_date = date(year, start_month, start_day)
            end_date = start_date + relativedelta(years=1, days=-1)
        
        return start_date, end_date
    
    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    
    @api.constrains('bce_number')
    def _check_bce_number(self):
        """Validate Belgian BCE number format and check digit"""
        for company in self:
            if company.bce_number:
                clean = re.sub(r'[.\s-]', '', company.bce_number)
                if not re.match(r'^\d{10}$', clean):
                    raise ValidationError(_(
                        "Le numéro BCE doit contenir 10 chiffres (format: 0XXX.XXX.XXX)"
                    ))
                # Validate check digit (modulo 97)
                base = int(clean[:8])
                check = int(clean[8:])
                expected = 97 - (base % 97)
                if check != expected:
                    raise ValidationError(_(
                        "Le numéro BCE %(number)s est invalide (chiffre de contrôle incorrect). "
                        "Attendu: %(expected)02d",
                        number=company.get_bce_number_formatted(),
                        expected=expected,
                    ))
    
    @api.constrains('fiscal_year_start_day')
    def _check_fiscal_year_start_day(self):
        """Validate fiscal year start day"""
        for company in self:
            if company.fiscal_year_start_day and not (1 <= company.fiscal_year_start_day <= 28):
                raise ValidationError(_(
                    "Le jour de début d'exercice doit être entre 1 et 28"
                ))
