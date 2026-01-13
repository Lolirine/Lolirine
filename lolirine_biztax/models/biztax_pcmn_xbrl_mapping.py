# -*- coding: utf-8 -*-
"""
Comprehensive mapping between Belgian PCMN (Plan Comptable Minimum Normalisé)
and XBRL be-tax taxonomy concepts.

This module provides:
- Complete PCMN → XBRL element mapping
- Automatic detection of fiscal adjustment needs
- Support for both MAR (Minimum Algemeen Rekeningstelsel) and extended charts
"""
from odoo import api, fields, models, _


class BiztaxPcmnXbrlMapping(models.Model):
    """
    Maps Belgian chart of accounts (PCMN/MAR) to XBRL taxonomy elements.
    Used for automatic data extraction and fiscal adjustment detection.
    """
    _name = 'biztax.pcmn.xbrl.mapping'
    _description = 'Mapping PCMN → XBRL be-tax'
    _order = 'pcmn_code'
    _rec_name = 'display_name'

    # === PCMN IDENTIFICATION ===
    pcmn_code = fields.Char(
        string='Code PCMN',
        required=True,
        index=True,
        help="Code du plan comptable belge (ex: 600, 6100, 61310)",
    )
    pcmn_code_to = fields.Char(
        string='Code PCMN fin',
        help="Pour définir une plage de comptes (ex: 600 à 609)",
    )
    pcmn_name = fields.Char(
        string='Libellé PCMN',
        required=True,
        translate=True,
    )
    pcmn_class = fields.Selection([
        ('1', 'Classe 1 - Fonds propres, provisions, dettes à LT'),
        ('2', 'Classe 2 - Frais d\'établissement, actifs immobilisés'),
        ('3', 'Classe 3 - Stocks et commandes en cours'),
        ('4', 'Classe 4 - Créances et dettes à CT'),
        ('5', 'Classe 5 - Placements de trésorerie et valeurs disponibles'),
        ('6', 'Classe 6 - Charges'),
        ('7', 'Classe 7 - Produits'),
    ], string='Classe PCMN', compute='_compute_pcmn_class', store=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    # === XBRL MAPPING ===
    xbrl_element = fields.Char(
        string='Élément XBRL',
        help="Nom de l'élément dans la taxonomie be-tax",
    )
    xbrl_concept_id = fields.Char(
        string='ID Concept XBRL',
        help="Identifiant unique du concept XBRL",
    )
    tax_code_id = fields.Many2one(
        'biztax.tax.code',
        string='Code fiscal',
        help="Code fiscal correspondant pour la déclaration",
    )

    # === FISCAL TREATMENT ===
    fiscal_category = fields.Selection([
        # Résultat comptable
        ('pnl_revenue', 'Produits (classe 7)'),
        ('pnl_expense', 'Charges (classe 6)'),
        # Bilan
        ('bs_asset', 'Actif'),
        ('bs_liability', 'Passif'),
        ('bs_equity', 'Fonds propres'),
        # DNA Categories
        ('dna_car', 'DNA - Frais de voiture'),
        ('dna_restaurant', 'DNA - Frais de restaurant'),
        ('dna_reception', 'DNA - Frais de réception'),
        ('dna_gift', 'DNA - Cadeaux d\'affaires'),
        ('dna_clothing', 'DNA - Frais de vêtements'),
        ('dna_fine', 'DNA - Amendes et pénalités'),
        ('dna_pension', 'DNA - Pensions et cotisations'),
        ('dna_provision', 'DNA - Provisions'),
        ('dna_interest', 'DNA - Intérêts excessifs'),
        ('dna_tax', 'DNA - Impôts non déductibles'),
        ('dna_other', 'DNA - Autres'),
        # Déductions
        ('ded_rdt', 'Déduction - RDT'),
        ('ded_innovation', 'Déduction - Innovation'),
        ('ded_investment', 'Déduction - Investissement'),
        ('ded_patent', 'Déduction - Brevet'),
        ('ded_nid', 'Déduction - Intérêts notionnels'),
        # Plus-values
        ('pv_normal', 'Plus-value - Régime normal'),
        ('pv_spread', 'Plus-value - Taxation étalée'),
        ('pv_exempt', 'Plus-value - Immunisée'),
        # Provisions
        ('prov_deductible', 'Provision - Déductible'),
        ('prov_non_deductible', 'Provision - Non déductible'),
        # Amortissements
        ('dep_normal', 'Amortissement - Normal'),
        ('dep_accelerated', 'Amortissement - Accéléré'),
        ('dep_excess', 'Amortissement - Excédentaire'),
        # Réserves
        ('res_legal', 'Réserve légale'),
        ('res_available', 'Réserve disponible'),
        ('res_unavailable', 'Réserve indisponible'),
        # Autres
        ('other', 'Autre'),
    ], string='Catégorie fiscale', required=True, default='other')

    # === DNA CONFIGURATION ===
    requires_dna_adjustment = fields.Boolean(
        string='Requiert ajustement DNA',
        default=False,
    )
    dna_percentage = fields.Float(
        string='% DNA standard',
        help="Pourcentage de DNA applicable par défaut",
    )
    dna_variable = fields.Boolean(
        string='DNA variable',
        default=False,
        help="Le pourcentage DNA dépend de facteurs externes (ex: CO2 véhicule)",
    )
    dna_legal_reference = fields.Char(
        string='Base légale DNA',
        help="Article du CIR92",
    )

    # === DEDUCTION CONFIGURATION ===
    is_deductible_base = fields.Boolean(
        string='Base de déduction',
        default=False,
        help="Ce compte sert de base pour calcul de déduction",
    )
    deduction_type = fields.Selection([
        ('rdt', 'RDT - Revenus définitivement taxés'),
        ('innovation', 'Déduction innovation'),
        ('investment', 'Déduction investissement'),
        ('nid', 'Intérêts notionnels'),
        ('patent', 'Déduction brevet'),
        ('donation', 'Libéralités'),
    ], string='Type de déduction')
    deduction_rate = fields.Float(
        string='Taux de déduction',
        help="Pourcentage de déduction applicable",
    )

    # === SPECIAL TREATMENTS ===
    requires_manual_review = fields.Boolean(
        string='Vérification manuelle requise',
        default=False,
    )
    review_reason = fields.Text(
        string='Raison de la vérification',
    )

    # === ANNEXES ===
    requires_annex = fields.Boolean(
        string='Annexe requise',
        default=False,
    )
    annex_type = fields.Selection([
        ('275C', '275C - Provisions pour risques et charges'),
        ('275U', '275U - Plus-values'),
        ('275W', '275W - Recherche et développement'),
        ('275N', '275N - Intérêts notionnels'),
        ('275F', '275F - Frais de voiture'),
        ('275P', '275P - Pertes professionnelles'),
        ('275K', '275K - Déduction pour investissement'),
        ('275A', '275A - Réductions d\'impôt'),
        ('328S', '328S - Secret commissionnel'),
        ('328K', '328K - Voitures de société'),
    ], string='Type d\'annexe')

    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    @api.depends('pcmn_code')
    def _compute_pcmn_class(self):
        for rec in self:
            if rec.pcmn_code and len(rec.pcmn_code) > 0:
                rec.pcmn_class = rec.pcmn_code[0]
            else:
                rec.pcmn_class = False

    @api.depends('pcmn_code', 'pcmn_name')
    def _compute_display_name(self):
        for rec in self:
            if rec.pcmn_code_to:
                rec.display_name = f"{rec.pcmn_code}-{rec.pcmn_code_to} {rec.pcmn_name}"
            else:
                rec.display_name = f"{rec.pcmn_code} {rec.pcmn_name}"

    def get_accounts_for_mapping(self, company_id):
        """Get all Odoo accounts that match this PCMN mapping"""
        self.ensure_one()
        domain = [('company_id', '=', company_id)]
        
        if self.pcmn_code_to:
            # Range of accounts
            domain.append(('code', '>=', self.pcmn_code))
            domain.append(('code', '<=', self.pcmn_code_to + 'z'))
        else:
            # Single account or prefix
            domain.append(('code', '=like', self.pcmn_code + '%'))
        
        return self.env['account.account'].search(domain)


class BiztaxPcmnMappingWizard(models.TransientModel):
    """Wizard to apply PCMN mappings to a company"""
    _name = 'biztax.pcmn.mapping.wizard'
    _description = 'Assistant configuration mapping PCMN'

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    chart_type = fields.Selection([
        ('mar', 'MAR - Plan comptable minimum'),
        ('full', 'PCMN complet'),
        ('custom', 'Personnalisé'),
    ], string='Type de plan comptable', default='mar', required=True)
    
    overwrite_existing = fields.Boolean(
        string='Écraser les mappings existants',
        default=False,
    )

    def action_apply_mappings(self):
        """Apply PCMN→XBRL mappings to the selected company"""
        self.ensure_one()
        
        AccountMapping = self.env['biztax.account.mapping']
        PcmnMapping = self.env['biztax.pcmn.xbrl.mapping']
        
        if self.overwrite_existing:
            # Remove existing mappings for this company
            AccountMapping.search([
                ('company_id', '=', self.company_id.id)
            ]).unlink()
        
        # Get all PCMN mappings that require DNA adjustment
        pcmn_mappings = PcmnMapping.search([
            ('requires_dna_adjustment', '=', True),
            ('active', '=', True),
        ])
        
        created_count = 0
        for pcmn in pcmn_mappings:
            if pcmn.tax_code_id and pcmn.dna_percentage:
                # Check if mapping already exists
                existing = AccountMapping.search([
                    ('company_id', '=', self.company_id.id),
                    ('account_code_prefix', '=', pcmn.pcmn_code),
                ], limit=1)
                
                if not existing:
                    AccountMapping.create({
                        'name': pcmn.pcmn_name,
                        'company_id': self.company_id.id,
                        'account_code_prefix': pcmn.pcmn_code,
                        'tax_code_id': pcmn.tax_code_id.id,
                        'dna_percentage': pcmn.dna_percentage,
                        'category': 'dna' if pcmn.requires_dna_adjustment else 'other',
                        'adjustment_type': 'increase',
                    })
                    created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mappings créés'),
                'message': _('%d mappings PCMN → Fiscal créés pour %s') % (
                    created_count, self.company_id.name
                ),
                'type': 'success',
                'sticky': False,
            }
        }
