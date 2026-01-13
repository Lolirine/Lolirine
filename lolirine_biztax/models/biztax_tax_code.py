# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class BiztaxTaxCode(models.Model):
    """
    Tax codes from be-tax taxonomy
    These correspond to the XBRL elements in the Belgian tax declaration
    """
    _name = 'biztax.tax.code'
    _description = 'Code fiscal be-tax'
    _order = 'section, code'
    _rec_name = 'display_name'

    code = fields.Char(
        string='Code',
        required=True,
        index=True,
    )
    name = fields.Char(
        string='Libellé',
        required=True,
        translate=True,
    )
    name_nl = fields.Char(string='Libellé (NL)')
    name_de = fields.Char(string='Libellé (DE)')
    
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )
    
    # XBRL mapping
    xbrl_element = fields.Char(
        string='Élément XBRL',
        help="Nom de l'élément dans la taxonomie be-tax",
    )
    xbrl_namespace = fields.Selection([
        ('rcorp', 'be-tax-inc-rcorp'),
        ('nrcorp', 'be-tax-inc-nrcorp'),
        ('rle', 'be-tax-inc-rle'),
    ], string='Namespace XBRL')
    
    # Classification
    declaration_type = fields.Selection([
        ('rcorp', 'Impôt des sociétés'),
        ('rle', 'Impôt des personnes morales'),
        ('nrcorp', 'Impôt des non-résidents'),
        ('all', 'Tous'),
    ], string='Type déclaration', default='all')
    
    section = fields.Selection([
        ('F', 'Cadre F - Première opération'),
        ('G', 'Cadre G - Détail des bénéfices'),
        ('H', 'Cadre H - Détail des pertes'),
        ('I', 'Cadre I - Deuxième opération'),
        ('J', 'Cadre J - Déductions'),
        ('K', 'Cadre K - Base imposable'),
        ('L', 'Cadre L - Impôt'),
        ('M', 'Cadre M - Précomptes'),
        ('N', 'Cadre N - Solde'),
        ('O', 'Cadre O - Autres'),
        ('annexe', 'Annexes'),
    ], string='Section/Cadre')
    
    # Default values for adjustments
    default_category = fields.Selection([
        ('dna', 'Dépenses Non Admises (DNA)'),
        ('reserve', 'Mouvement de réserves'),
        ('provision', 'Provisions'),
        ('depreciation', 'Amortissements'),
        ('plus_value', 'Plus-values'),
        ('deduction', 'Déductions'),
        ('exemption', 'Exonérations'),
        ('loss_carryforward', 'Pertes antérieures'),
        ('rdi', 'Revenus définitivement imposés (RDI)'),
        ('innovation', 'Déduction pour innovation'),
        ('investment', "Déduction pour investissement"),
        ('other', 'Autres'),
    ], string='Catégorie par défaut')
    
    default_adjustment_type = fields.Selection([
        ('increase', 'Majoration'),
        ('decrease', 'Diminution'),
    ], string='Type par défaut')
    
    # Data type for XBRL
    data_type = fields.Selection([
        ('monetary', 'Montant'),
        ('integer', 'Entier'),
        ('decimal', 'Décimal'),
        ('string', 'Texte'),
        ('boolean', 'Booléen'),
        ('date', 'Date'),
    ], string='Type de donnée', default='monetary')
    
    # Constraints
    is_mandatory = fields.Boolean(string='Obligatoire')
    min_value = fields.Float(string='Valeur minimum')
    max_value = fields.Float(string='Valeur maximum')
    
    # Hierarchical structure
    parent_id = fields.Many2one(
        'biztax.tax.code',
        string='Code parent',
        ondelete='cascade',
    )
    child_ids = fields.One2many(
        'biztax.tax.code',
        'parent_id',
        string='Codes enfants',
    )
    
    description = fields.Text(string='Description')
    legal_reference = fields.Char(string='Référence légale (CIR92)')
    
    active = fields.Boolean(default=True)
    
    taxonomy_version = fields.Selection([
        ('2025-04-30', 'be-tax-2025-04-30'),
        ('2024-04-30', 'be-tax-2024-04-30'),
    ], string='Version taxonomie', default='2025-04-30')

    _sql_constraints = [
        ('code_taxonomy_uniq', 'unique(code, taxonomy_version)', 
         'Le code doit être unique par version de taxonomie.')
    ]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f"[{record.code}] {record.name}"))
        return result

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)
