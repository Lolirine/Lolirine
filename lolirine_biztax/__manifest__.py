# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Biztax - Déclaration ISOC Belgique',
    'version': '19.0.4.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Génération des déclarations ISOC belges au format XBRL/Biztax',
    'description': """
Lolirine Biztax - Déclaration ISOC Belgique
============================================

Module pour la génération des déclarations fiscales belges (ISOC/VenB/IPM/INR) 
au format XBRL conforme à la taxonomie be-tax pour dépôt sur Biztax/MyMinfin.

Fonctionnalités principales:
----------------------------
* Calcul automatique de la base imposable depuis la comptabilité Odoo (classes 6 & 7)
* Gestion des ajustements fiscaux (DNA, RDT, NID, provisions, plus-values, etc.)
* Support déclarations initiales et correctives
* Génération instance XBRL conforme à la taxonomie be-tax (2023-2025)
* Assemblage fichier .biztax (ZIP avec manifest + annexes PDF)
* Génération automatique des annexes PDF (Bilan, Compte de résultats, DNA)
* Gestion des annexes PDF manuelles (275C, 275W, etc.)
* Configuration société : BCE, forme juridique, siège social
* Interface de configuration dans Paramètres → Biztax

Types de déclarations:
----------------------
* ISOC - Impôt des sociétés
* IPM - Impôt des personnes morales
* INR - Impôt des non-résidents/sociétés

Catégories d'ajustements supportées:
------------------------------------
* DNA (Dépenses Non Admises) : restaurant, réception, cadeaux, amendes, véhicules CO2
* Provisions non déductibles
* Amortissements non admis
* Plus-values (normales, étalées, immunisées)
* Déductions : RDT, innovation, investissement, NID
* Report de pertes (règle des 70%)

Rapports PDF générés automatiquement:
-------------------------------------
* Bilan (structure PCMN belge)
* Compte de résultats (structure PCMN belge)
* Détail des DNA (dépenses non admises)
* Résumé fiscal complet

Configuration requise:
----------------------
* Module de comptabilité belge (l10n_be)
* Plan comptable PCMN configuré
* Numéro d'entreprise BCE configuré dans les paramètres société
""",
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'l10n_be',
        'mail',
    ],
    'data': [
        # Security (FIRST)
        'security/biztax_security.xml',
        'security/ir.model.access.csv',
        
        # Reference Data
        'data/biztax_tax_code_data.xml',
        'data/biztax_declaration_type_data.xml',
        
        # Reports - before views that reference them
        'report/biztax_report_actions.xml',
        'report/report_balance_sheet.xml',
        'report/report_profit_loss.xml',
        'report/report_dna_detail.xml',
        'report/report_fiscal_summary.xml',
        
        # Views - Base models first
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/biztax_declaration_type_views.xml',
        'views/biztax_tax_code_views.xml',
        'views/biztax_attachment_views.xml',
        'views/biztax_adjustment_views.xml',
        'views/biztax_declaration_views.xml',
        
        # Wizards
        'wizards/biztax_declaration_wizard_views.xml',
        
        # Menus (LAST - references all actions)
        'views/biztax_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
