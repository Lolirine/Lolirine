# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Biztax - Déclaration ISOC Belgique',
    'version': '19.0.1.0.1',
    'category': 'Accounting/Localizations',
    'summary': 'Génération des déclarations ISOC belges au format XBRL/Biztax',
    'description': """
Lolirine Biztax - Déclaration ISOC Belgique
============================================

Module pour la génération des déclarations fiscales belges (ISOC/VenB) 
au format XBRL conforme à la taxonomie be-tax pour dépôt sur Biztax/MyMinfin.

Fonctionnalités principales:
----------------------------
* Calcul automatique de la base imposable depuis la comptabilité Odoo
* Gestion des ajustements fiscaux (DNA, provisions, plus-values, etc.)
* Génération XBRL conforme à la taxonomie be-tax
* Export fichier .biztax pour dépôt sur MyMinfin

Catégories d'ajustements supportées:
------------------------------------
* DNA (Dépenses Non Admises) : restaurant, réception, cadeaux, amendes, véhicules
* Provisions non déductibles
* Amortissements non admis
* Plus-values (normales, étalées, immunisées)
* Déductions : RDT, innovation, investissement, NID
* Report de pertes

Configuration requise:
----------------------
* Module de comptabilité belge (l10n_be)
* Plan comptable PCMN configuré
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
        # Security
        'security/biztax_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/biztax_tax_code_data.xml',
        # Views
        'views/biztax_menus.xml',
        'views/biztax_declaration_views.xml',
        'views/biztax_adjustment_views.xml',
        'views/biztax_tax_code_views.xml',
        # Wizards
        'wizards/biztax_declaration_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
