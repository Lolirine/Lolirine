# -*- coding: utf-8 -*-
{
    'name': 'Lolirine — Fiche de visite piscine',
    'version': '19.0.1.0.0',
    'summary': 'Check-list d\'intervention piscine avec recherche produits catalogue',
    'description': """
        Module de gestion des fiches de visite chantier piscine pour
        Lolirine Pool Store.

        Fonctionnalités :
        - 6 types d'intervention (construction, rénovation, entretien,
          hivernage, remise en route, changement de matériel)
        - 6 plans de bassins (rectangulaire, carré, L, ovale, haricot, spa)
        - Formulaire client/technicien/date/référence
        - Cases à cocher avec progression en temps réel
        - Recherche de produits dans le catalogue Pool Store (website_id=6)
        - Suggestions IA via API Anthropic si catalogue non accessible
        - Récapitulatif matériaux avec total estimatif HT
        - Impression / téléchargement PDF optimisé A4
        - Page dédiée sur le site Pool Store (/visite-chantier)
        - Accès restreint aux utilisateurs internes (techniciens)
    """,
    'author': 'Lolirine SRL',
    'website': 'https://www.lolirinepoolstore.be',
    'category': 'Website',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # React + ReactDOM via CDN (chargés dans le template)
        ],
        # Assets propres au module (chargés uniquement sur la page checklist)
        'lolirine_pool_checklist.assets_checklist': [
            'lolirine_pool_checklist/static/src/js/pool_checklist.js',
            'lolirine_pool_checklist/static/src/css/pool_checklist.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
