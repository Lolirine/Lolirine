# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Popup Personnalisé',
    'version': '19.0.3.2.0',
    'category': 'Website',
    'summary': 'Popup personnalisable avec gestion multi-pages et boxes disponibles',
    'description': """
        Popup personnalisé pour Lolirine Garde-Meubles
        ===============================================
        
        Fonctionnalités :
        - Gestion de plusieurs popups avec activation/désactivation
        - Type Standard : Titre, texte et bouton personnalisables
        - Type Boxes Disponibles : Affiche automatiquement les boxes libres
        - Sélection de pages spécifiques (Many2many)
        - Sélection de catégories de produits (Many2many)
        - URLs personnalisées
        - Priorité entre les popups
        - Statistiques de vues et clics
        - Design aux couleurs Lolirine
    """,
    'author': 'Lolirine',
    'website': 'https://lolirine.be',
    'depends': ['website', 'website_sale', 'lolirine_storage_availability'],
    'data': [
        'security/ir.model.access.csv',
        'views/popup_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/popup_template.xml',
        'views/menu.xml',
        'data/popup_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_popup/static/src/css/popup.css',
            'lolirine_popup/static/src/js/popup.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
