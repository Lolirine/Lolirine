# -*- coding: utf-8 -*-
{
    'name': 'Indemnités Kilométriques',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Gestion des trajets professionnels et calcul des indemnités kilométriques',
    'description': """
Indemnités Kilométriques - Gestion des Trajets Professionnels
==============================================================

Ce module permet de gérer les trajets professionnels effectués avec un véhicule 
personnel ou de société et de calculer automatiquement les indemnités kilométriques 
pour la déduction fiscale.

Fonctionnalités principales:
----------------------------
* Enregistrement des trajets avec points de départ et d'arrivée
* Calcul automatique des distances (ou saisie manuelle)
* Liaison avec le parc automobile (véhicules de société ou personnels)
* Barème kilométrique configurable selon la puissance fiscale
* Génération de notes de frais automatiques
* Rapports mensuels et annuels pour la comptabilité
* Intégration avec le module de comptabilité

Configuration:
--------------
* Définir les barèmes kilométriques selon la législation en vigueur
* Configurer les véhicules (personnels ou de société)
* Définir les catégories de trajets (client, fournisseur, administratif, etc.)

Ce module est idéal pour:
-------------------------
* Les indépendants et gérants de société
* Les commerciaux et techniciens itinérants
* La gestion des déplacements professionnels
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_expense',
        'fleet',
        'account',
        'calendar',
    ],
    'data': [
        # Security
        'security/km_expense_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/km_expense_data.xml',
        'data/km_bareme_data.xml',
        # Views sans menus
        'views/km_expense_views.xml',
        'views/km_trajet_views.xml',
        'views/km_bareme_views.xml',
        'views/km_vehicule_views.xml',
        'views/account_move_views.xml',
        # Menus principaux (avec actions)
        'views/km_expense_menus.xml',
        # Vues avec sous-menus (après les menus principaux)
        'views/km_destination_views.xml',
        'views/res_partner_views.xml',
        # Config settings
        'views/res_config_settings_views.xml',
        # Data avec références aux modèles
        'data/km_lieux_destinations_data.xml',
        'data/km_cron_data.xml',
        # Wizard
        'wizard/km_expense_generate_wizard_views.xml',
        'wizard/km_trajet_from_invoice_wizard_views.xml',
        'wizard/km_comptabilisation_wizard_views.xml',
        # Reports
        'reports/km_expense_report.xml',
        'reports/km_expense_report_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'km_expense/static/src/js/address_autocomplete.js',
            'km_expense/static/src/xml/address_autocomplete.xml',
        ],
    },
    'images': ['static/description/icon.png'],
}
