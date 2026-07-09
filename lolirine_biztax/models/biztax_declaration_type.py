# -*- coding: utf-8 -*-
"""
Declaration Types for Belgian Tax Declarations
ISoc (Corporate Income Tax), IPM (Legal Entities Tax), INR (Non-Resident Tax)
"""
from odoo import api, fields, models, _


class BiztaxDeclarationType(models.Model):
    _name = 'biztax.declaration.type'
    _description = 'Type de déclaration fiscale'
    _order = 'sequence, code'

    name = fields.Char(
        string="Nom",
        required=True,
        translate=True,
    )
    
    code = fields.Char(
        string="Code",
        required=True,
        size=10,
    )
    
    sequence = fields.Integer(
        string="Séquence",
        default=10,
    )
    
    active = fields.Boolean(
        string="Actif",
        default=True,
    )
    
    description = fields.Text(
        string="Description",
        translate=True,
    )
    
    tax_type = fields.Selection([
        ('isoc', 'Impôt des Sociétés (ISoc)'),
        ('ipm', 'Impôt des Personnes Morales (IPM)'),
        ('inr_soc', 'Impôt des Non-Résidents/Sociétés (INR-Soc)'),
        ('inr_pm', 'Impôt des Non-Résidents/PM (INR-PM)'),
    ], string="Type d'impôt", required=True, default='isoc')
    
    # XBRL Configuration
    xbrl_namespace = fields.Char(
        string="Namespace XBRL",
        help="Namespace pour le fichier XBRL",
    )
    
    xbrl_schema = fields.Char(
        string="Schéma XSD",
        help="URL du schéma XSD de la taxonomie",
    )
    
    # Legal forms allowed
    allowed_legal_forms = fields.Char(
        string="Formes juridiques autorisées",
        help="Liste des codes de formes juridiques autorisées (séparés par virgule), vide = toutes",
    )
    
    # Required annexes
    required_annexe_type_ids = fields.Many2many(
        'biztax.annexe.type',
        'biztax_declaration_type_annexe_rel',
        'declaration_type_id',
        'annexe_type_id',
        string="Annexes obligatoires",
    )
    
    # Optional annexes
    optional_annexe_type_ids = fields.Many2many(
        'biztax.annexe.type',
        'biztax_declaration_type_optional_annexe_rel',
        'declaration_type_id',
        'annexe_type_id',
        string="Annexes optionnelles",
    )
    
    # Tax codes applicable
    tax_code_ids = fields.Many2many(
        'biztax.tax.code',
        'biztax_declaration_type_tax_code_rel',
        'declaration_type_id',
        'tax_code_id',
        string="Codes fiscaux applicables",
    )
    
    _code_unique = models.Constraint(
        'UNIQUE(code)',
        "Le code du type de déclaration doit être unique",
    )
    
    def name_get(self):
        """Display name with code"""
        return [(rec.id, f"[{rec.code}] {rec.name}") for rec in self]


class BiztaxAnnexeType(models.Model):
    _name = 'biztax.annexe.type'
    _description = 'Type d\'annexe Biztax'
    _order = 'sequence, code'
    
    name = fields.Char(
        string="Nom",
        required=True,
        translate=True,
    )
    
    code = fields.Char(
        string="Code",
        required=True,
        size=20,
    )
    
    sequence = fields.Integer(
        string="Séquence",
        default=10,
    )
    
    active = fields.Boolean(
        string="Actif",
        default=True,
    )
    
    description = fields.Text(
        string="Description",
        translate=True,
        help="Description de l'annexe et son contenu attendu",
    )
    
    annexe_category = fields.Selection([
        ('financial', 'États financiers'),
        ('fiscal', 'Documents fiscaux'),
        ('legal', 'Documents légaux'),
        ('other', 'Autres'),
    ], string="Catégorie", default='fiscal')
    
    # Generation options
    can_auto_generate = fields.Boolean(
        string="Génération automatique",
        default=False,
        help="Cette annexe peut être générée automatiquement depuis Odoo",
    )
    
    report_id = fields.Many2one(
        'ir.actions.report',
        string="Rapport Odoo",
        help="Rapport à utiliser pour la génération automatique",
        domain="[('report_type', '=', 'qweb-pdf')]",
    )
    
    template_id = fields.Many2one(
        'ir.ui.view',
        string="Template QWeb",
        help="Template QWeb personnalisé pour la génération",
    )
    
    # XBRL mapping
    xbrl_element = fields.Char(
        string="Élément XBRL",
        help="Nom de l'élément dans la taxonomie XBRL",
    )
    
    # Conditions
    condition_field = fields.Char(
        string="Champ de condition",
        help="Champ à vérifier pour déterminer si l'annexe est requise (ex: total_increases > 0)",
    )
    
    # File requirements
    max_file_size_mb = fields.Float(
        string="Taille max (MB)",
        default=10.0,
    )
    
    allowed_mime_types = fields.Char(
        string="Types MIME autorisés",
        default="application/pdf",
        help="Types MIME autorisés, séparés par virgule",
    )
    
    code_unique = models.Constraint(
        'UNIQUE(code)',
        "Le code du type d'annexe doit être unique",
    )
    
    def name_get(self):
        """Display name with code"""
        return [(rec.id, f"[{rec.code}] {rec.name}") for rec in self]
