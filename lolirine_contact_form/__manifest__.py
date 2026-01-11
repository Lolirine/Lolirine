# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Formulaire Contact Optimisé',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Formulaire de contact optimisé pour la création d\'abonnements garde-meubles',
    'description': '''
        Ce module optimise le formulaire de contact pour :
        - Collecter toutes les informations nécessaires à la création d'un abonnement
        - Autocomplétion des adresses belges
        - Création automatique de leads/opportunités
        - Conversion facile en client et abonnement
    ''',
    'author': 'Lolirine SPRL',
    'website': 'https://lolirine-lolirine.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'crm',
        'sale_subscription',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_stage_data.xml',
        'views/contact_form_template.xml',
        'views/crm_lead_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_contact_form/static/src/js/address_autocomplete.js',
            'lolirine_contact_form/static/src/css/contact_form.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
