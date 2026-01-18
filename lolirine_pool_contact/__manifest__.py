# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Store - Contact',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Page Contactez-nous pour Pool Store avec formulaire CRM',
    'description': """
        Page Contact pour Lolirine Pool Store
        ======================================
        
        PAGE CONTACTEZ-NOUS :
        - Formulaire avec choix du type de demande
        - Support Particulier / Professionnel
        - Informations piscine optionnelles
        - Création automatique d'opportunités CRM
        - Design responsive moderne
        
        TYPES DE DEMANDE :
        - Question sur un produit
        - Demande de service
        - Demande de devis
        - Question générale
        
        URL : /pool/contact
        
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
        'views/contact_page.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_contact/static/src/css/contact.css',
            'lolirine_pool_contact/static/src/js/contact_form.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
