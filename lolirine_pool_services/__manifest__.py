# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Store - Services',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Pages de services et formulaire devis CRM pour Pool Store',
    'description': """
        Module de services pour Lolirine Pool Store
        ============================================
        
        PAGES DE SERVICES :
        - Page principale "Nos Services"
        - Entretien & Réparation
        - Construction & Rénovation  
        - Analyse de l'eau
        - Hivernage & Estivage
        - Formules d'entretien
        
        FORMULAIRE DE CONTACT :
        - Page "Demande de devis" dédiée Pool Store
        - Création automatique d'opportunités CRM
        - Champs spécifiques piscine
        
        Contact : +32 497 44 41 46 / info@lolirinepoolstore.be
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_data.xml',
        'views/crm_lead_views.xml',
        'views/service_pages.xml',
        'views/contact_page.xml',
        'data/website_pages.xml',
        'data/website_menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_services/static/src/css/services.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
