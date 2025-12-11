# -*- coding: utf-8 -*-
{
    'name': 'ACT365 Integration - Contrôle d\'Accès',
    'version': '18.0.1.0.0',
    'category': 'Services/Access Control',
    'summary': 'Intégration ACT365 pour la gestion des codes d\'accès garde-meubles',
    'description': """
ACT365 Integration pour Odoo 18
===============================

Ce module permet d'intégrer le système de contrôle d'accès ACT365 avec 
les abonnements Odoo pour la gestion automatique des codes d'accès.

Fonctionnalités:
----------------
* Configuration API ACT365 (clé API, URL)
* Attribution automatique de codes PIN aux abonnés
* Synchronisation des cardholders avec ACT365
* Affichage du code d'accès sur la fiche client et l'abonnement
* Gestion des groupes de cardholders ACT365
* Activation/Désactivation automatique selon l'état de l'abonnement

Configuration requise:
----------------------
1. Créer une clé API dans ACT365 (Profile > Apps & Integrations)
2. Configurer l'URL API et la clé dans Odoo (Paramètres > Intégrations > ACT365)
3. Sélectionner le groupe de cardholders par défaut

    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale_subscription',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/act365_data.xml',
        'views/res_config_settings_views.xml',
        'views/sale_subscription_views.xml',
        'views/res_partner_views.xml',
        'wizard/act365_assign_code_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
