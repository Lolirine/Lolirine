# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Popup Personnalisé',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Popup personnalisable pour redirection vers formulaire de contact',
    'description': """
        Popup personnalisé pour Lolirine Garde-Meubles
        ===============================================
        
        Fonctionnalités :
        - Popup configurable depuis le backend
        - Titre, texte et bouton personnalisables
        - Lien de redirection configurable
        - Délai d'affichage paramétrable
        - Durée de masquage après fermeture
        - Choix des pages où afficher le popup
        - Design aux couleurs Lolirine
    """,
    'author': 'Lolirine',
    'website': 'https://lolirine.be',
    'depends': ['website', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/popup_config_views.xml',
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
