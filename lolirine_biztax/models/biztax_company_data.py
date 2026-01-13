# -*- coding: utf-8 -*-
"""
Extended company data management for Biztax declarations.
Automatically retrieves and validates all required company information.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import re


class ResCompanyBiztaxExtended(models.Model):
    """
    Extended company information required for Biztax declarations.
    All fields needed for XBRL identification and filing.
    """
    _inherit = 'res.company'

    # === BCE/KBO IDENTIFICATION ===
    enterprise_number = fields.Char(
        string="Numéro d'entreprise (BCE/KBO)",
        help="Format: 0XXX.XXX.XXX ou XXXX.XXX.XXX",
        compute='_compute_enterprise_number',
        store=True,
    )
    enterprise_number_formatted = fields.Char(
        string="N° entreprise formaté",
        compute='_compute_enterprise_number',
        store=True,
    )
    
    # === LEGAL INFORMATION ===
    legal_form_code = fields.Char(
        string='Code forme juridique',
        compute='_compute_legal_form_code',
        store=True,
    )
    foundation_date = fields.Date(
        string='Date de constitution',
    )
    fiscal_year_closing_month = fields.Selection([
        ('1', 'Janvier'), ('2', 'Février'), ('3', 'Mars'),
        ('4', 'Avril'), ('5', 'Mai'), ('6', 'Juin'),
        ('7', 'Juillet'), ('8', 'Août'), ('9', 'Septembre'),
        ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre'),
    ], string='Mois de clôture', default='12')
    
    # === NACE CODES ===
    nace_main_code = fields.Char(
        string='Code NACE principal',
        help="Code NACE-BEL 2008 de l'activité principale",
    )
    nace_main_description = fields.Char(
        string='Description NACE',
    )
    nace_secondary_ids = fields.One2many(
        'res.company.nace',
        'company_id',
        string='Codes NACE secondaires',
    )
    
    # === REGISTERED OFFICE ===
    registered_street = fields.Char(
        string='Rue (siège social)',
        compute='_compute_registered_address',
        store=True,
        readonly=False,
    )
    registered_street_number = fields.Char(
        string='Numéro',
        compute='_compute_registered_address',
        store=True,
        readonly=False,
    )
    registered_box = fields.Char(
        string='Boîte',
    )
    registered_zip = fields.Char(
        string='Code postal (siège)',
        compute='_compute_registered_address',
        store=True,
        readonly=False,
    )
    registered_city = fields.Char(
        string='Ville (siège)',
        compute='_compute_registered_address',
        store=True,
        readonly=False,
    )
    registered_country_code = fields.Char(
        string='Code pays',
        default='BE',
    )
    
    # === MANDATAIRES / DIRECTORS ===
    director_ids = fields.One2many(
        'res.company.director',
        'company_id',
        string='Mandataires / Administrateurs',
    )
    statutory_auditor = fields.Char(
        string='Commissaire aux comptes',
    )
    statutory_auditor_bce = fields.Char(
        string='BCE Commissaire',
    )
    
    # === DECLARANT INFORMATION ===
    declarant_type = fields.Selection([
        ('internal', 'Interne (dirigeant/employé)'),
        ('accountant', 'Expert-comptable externe'),
        ('tax_advisor', 'Conseil fiscal'),
    ], string='Type de déclarant', default='internal')
    declarant_name = fields.Char(
        string='Nom du déclarant',
    )
    declarant_quality = fields.Selection([
        ('admin', 'Administrateur'),
        ('manager', 'Gérant'),
        ('cfo', 'Directeur financier'),
        ('accountant', 'Comptable'),
        ('proxy', 'Mandataire'),
    ], string='Qualité du déclarant')
    declarant_national_number = fields.Char(
        string='N° national déclarant',
        help="Numéro de registre national (format: XX.XX.XX-XXX.XX)",
    )
    declarant_itaa_number = fields.Char(
        string='N° ITAA',
        help="Numéro d'inscription à l'ITAA pour expert-comptable/conseil fiscal",
    )
    
    # === BANK ACCOUNTS FOR TAX ===
    tax_bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Compte bancaire fiscal',
        domain="[('partner_id', '=', partner_id)]",
        help="Compte pour remboursements d'impôt",
    )
    tax_iban = fields.Char(
        string='IBAN fiscal',
        related='tax_bank_account_id.acc_number',
    )
    
    # === SME CRITERIA (Art. 15 CSA / WVV) ===
    sme_employees_fte = fields.Float(
        string='ETP moyen annuel',
        help="Équivalent temps plein moyen sur l'exercice",
    )
    sme_turnover = fields.Monetary(
        string='CA HTVA',
        currency_field='currency_id',
    )
    sme_balance_total = fields.Monetary(
        string='Total bilan',
        currency_field='currency_id',
    )
    sme_criteria_met = fields.Integer(
        string='Critères PME remplis',
        compute='_compute_sme_criteria',
    )
    is_small_company = fields.Boolean(
        string='Petite société (Art. 1:24 CSA)',
        compute='_compute_sme_criteria',
        store=True,
    )
    is_micro_company = fields.Boolean(
        string='Micro-société (Art. 1:25 CSA)',
        compute='_compute_sme_criteria',
        store=True,
    )
    
    # === GROUP STRUCTURE ===
    is_holding = fields.Boolean(
        string='Société holding',
    )
    is_consolidating = fields.Boolean(
        string='Société consolidante',
    )
    consolidated_company_ids = fields.Many2many(
        'res.company',
        'biztax_company_consolidation_rel',
        'parent_id',
        'child_id',
        string='Sociétés consolidées',
    )
    
    # === BIZTAX PORTAL ACCESS ===
    biztax_portal_user = fields.Char(
        string='Utilisateur portail Biztax',
    )
    biztax_last_filing_date = fields.Date(
        string='Dernière déclaration déposée',
    )

    @api.depends('vat')
    def _compute_enterprise_number(self):
        """Extract enterprise number from VAT number"""
        for company in self:
            if company.vat:
                # Remove BE prefix and spaces
                vat_clean = re.sub(r'[^0-9]', '', company.vat)
                if len(vat_clean) == 10:
                    # Format: 0XXX.XXX.XXX
                    company.enterprise_number = vat_clean
                    company.enterprise_number_formatted = f"{vat_clean[:4]}.{vat_clean[4:7]}.{vat_clean[7:]}"
                elif len(vat_clean) == 9:
                    # Old format without leading 0
                    company.enterprise_number = '0' + vat_clean
                    company.enterprise_number_formatted = f"0{vat_clean[:3]}.{vat_clean[3:6]}.{vat_clean[6:]}"
                else:
                    company.enterprise_number = vat_clean
                    company.enterprise_number_formatted = vat_clean
            else:
                company.enterprise_number = False
                company.enterprise_number_formatted = False

    @api.depends('legal_form')
    def _compute_legal_form_code(self):
        """Map legal form to official code"""
        code_map = {
            'SA': '014',
            'SRL': '015',
            'SC': '016',
            'SNC': '010',
            'SCS': '011',
            'SCA': '012',
            'ASBL': '020',
            'AISBL': '022',
            'Foundation': '030',
        }
        for company in self:
            company.legal_form_code = code_map.get(company.legal_form, '099')

    @api.depends('street', 'street2', 'zip', 'city')
    def _compute_registered_address(self):
        """Default registered address from company address"""
        for company in self:
            if not company.registered_street and company.street:
                # Parse street and number
                match = re.match(r'^(.+?),?\s*(\d+\w*)\s*$', company.street or '')
                if match:
                    company.registered_street = match.group(1).strip()
                    company.registered_street_number = match.group(2)
                else:
                    company.registered_street = company.street
            if not company.registered_zip:
                company.registered_zip = company.zip
            if not company.registered_city:
                company.registered_city = company.city

    @api.depends('sme_employees_fte', 'sme_turnover', 'sme_balance_total')
    def _compute_sme_criteria(self):
        """
        Compute SME status based on Belgian Company Code (CSA/WVV).
        Small company (Art. 1:24): max 1 of 3 criteria exceeded
        - Average employees: 50
        - Turnover (excl. VAT): 9,000,000 EUR
        - Balance sheet total: 4,500,000 EUR
        
        Micro company (Art. 1:25): max 1 of 3 criteria exceeded
        - Average employees: 10
        - Turnover: 700,000 EUR
        - Balance sheet total: 350,000 EUR
        """
        for company in self:
            # Small company criteria
            small_exceeded = 0
            if company.sme_employees_fte and company.sme_employees_fte > 50:
                small_exceeded += 1
            if company.sme_turnover and company.sme_turnover > 9000000:
                small_exceeded += 1
            if company.sme_balance_total and company.sme_balance_total > 4500000:
                small_exceeded += 1
            
            company.is_small_company = small_exceeded <= 1
            company.sme_criteria_met = 3 - small_exceeded
            
            # Micro company criteria
            micro_exceeded = 0
            if company.sme_employees_fte and company.sme_employees_fte > 10:
                micro_exceeded += 1
            if company.sme_turnover and company.sme_turnover > 700000:
                micro_exceeded += 1
            if company.sme_balance_total and company.sme_balance_total > 350000:
                micro_exceeded += 1
            
            company.is_micro_company = micro_exceeded <= 1

    def action_sync_from_bce(self):
        """
        Placeholder for BCE/KBO web service integration.
        In production, this would call the BCE API to retrieve company data.
        """
        self.ensure_one()
        # TODO: Implement BCE API call
        # API endpoint: https://kbopub.economie.fgov.be/kbo-open-data/
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronisation BCE'),
                'message': _('La synchronisation avec la BCE nécessite une clé API. '
                           'Veuillez configurer l\'accès dans les paramètres.'),
                'type': 'warning',
            }
        }

    def get_biztax_identification_data(self):
        """
        Retrieve all company identification data needed for XBRL.
        Returns a dictionary with all required fields.
        """
        self.ensure_one()
        
        errors = []
        if not self.enterprise_number:
            errors.append(_("Numéro d'entreprise (BCE) manquant"))
        if not self.legal_form:
            errors.append(_("Forme juridique non définie"))
        if not self.registered_zip or not self.registered_city:
            errors.append(_("Adresse du siège social incomplète"))
        
        if errors:
            raise UserError(_("Données société incomplètes:\n") + "\n".join(errors))
        
        return {
            'enterprise_number': self.enterprise_number,
            'enterprise_number_formatted': self.enterprise_number_formatted,
            'name': self.name,
            'legal_form': self.legal_form,
            'legal_form_code': self.legal_form_code,
            'nace_code': self.nace_main_code,
            'address': {
                'street': self.registered_street,
                'number': self.registered_street_number,
                'box': self.registered_box,
                'zip': self.registered_zip,
                'city': self.registered_city,
                'country': self.registered_country_code,
            },
            'declarant': {
                'name': self.declarant_name or self.biztax_contact_name,
                'quality': self.declarant_quality,
                'national_number': self.declarant_national_number,
                'itaa_number': self.declarant_itaa_number,
            },
            'is_small_company': self.is_small_company,
            'is_micro_company': self.is_micro_company,
            'fiscal_year_closing_month': self.fiscal_year_closing_month,
        }


class ResCompanyNace(models.Model):
    """Secondary NACE codes for company"""
    _name = 'res.company.nace'
    _description = 'Code NACE secondaire'

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        ondelete='cascade',
    )
    code = fields.Char(
        string='Code NACE',
        required=True,
    )
    description = fields.Char(
        string='Description',
    )
    is_main = fields.Boolean(
        string='Activité principale',
        default=False,
    )


class ResCompanyDirector(models.Model):
    """Company directors / mandataires for Biztax"""
    _name = 'res.company.director'
    _description = 'Mandataire / Administrateur'
    _order = 'sequence, name'

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
    )
    name = fields.Char(
        string='Nom',
        required=True,
    )
    
    director_type = fields.Selection([
        ('natural', 'Personne physique'),
        ('legal', 'Personne morale'),
    ], string='Type', default='natural', required=True)
    
    function = fields.Selection([
        ('admin', 'Administrateur'),
        ('admin_delegate', 'Administrateur délégué'),
        ('manager', 'Gérant'),
        ('ceo', 'CEO / Directeur général'),
        ('cfo', 'CFO / Directeur financier'),
        ('president', 'Président'),
        ('secretary', 'Secrétaire'),
        ('liquidator', 'Liquidateur'),
    ], string='Fonction', required=True)
    
    # Natural person
    national_number = fields.Char(
        string='N° national',
    )
    birth_date = fields.Date(
        string='Date de naissance',
    )
    
    # Legal person
    enterprise_number = fields.Char(
        string='N° entreprise (BCE)',
    )
    permanent_representative = fields.Char(
        string='Représentant permanent',
    )
    
    # Mandate
    mandate_start = fields.Date(
        string='Début mandat',
    )
    mandate_end = fields.Date(
        string='Fin mandat',
    )
    is_active = fields.Boolean(
        string='Mandat actif',
        default=True,
    )
    
    # Remuneration for declaration
    receives_remuneration = fields.Boolean(
        string='Perçoit une rémunération',
        default=True,
    )
    remuneration_amount = fields.Float(
        string='Rémunération brute annuelle',
    )
