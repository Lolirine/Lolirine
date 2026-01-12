# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Popup Personnalisé',
    'version': '19.0.2.0.0',
    'category': 'Website',
    'summary': 'Popup personnalisable avec affichage des boxes disponibles',
    'description': """
        Popup personnalisé pour Lolirine Garde-Meubles
        ===============================================
        
        Fonctionnalités :
        - Popup configurable depuis le backend
        - Type Standard : Titre, texte et bouton personnalisables
        - Type Boxes Disponibles : Affiche automatiquement les boxes libres
        - Lien de redirection vers formulaire de contact avec infos du box
        - Délai d'affichage paramétrable
        - Durée de masquage après fermeture
        - Choix des pages où afficher le popup
        - Design aux couleurs Lolirine
        - Statistiques de vues et clics
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
