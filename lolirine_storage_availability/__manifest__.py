# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Storage Availability',
    'version': '18.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Gestion de la disponibilité des box de stockage avec bouton rendez-vous',
    'description': """
Lolirine Storage Availability
=============================

Module de gestion de la disponibilité des box de stockage pour le e-commerce.

Fonctionnalités:
----------------
* Statut de disponibilité sur les produits (Disponible, Loué, Maintenance, Réservé)
* Bouton "Contactez-nous" sur le e-commerce avec lien vers la prise de rendez-vous
* Configuration globale dans les Paramètres généraux
* Configuration individuelle par produit (override possible)
* Intégration native avec le module website_appointment d'Odoo

Configuration:
--------------
1. Allez dans Configuration > Paramètres généraux > section "Box de Stockage"
2. Activez l'affichage du bouton rendez-vous
3. Sélectionnez le type de rendez-vous par défaut
4. Sur chaque produit, vous pouvez surcharger ces paramètres

Auteur: Lolirine SPRL
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'website_appointment',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ribbons.xml',
        'views/storage_menus.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/website_sale_templates.xml',
        'views/snippets.xml',
        'views/server_actions.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_storage_availability/static/src/css/storage_availability.css',
            'lolirine_storage_availability/static/src/js/storage_availability.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
