# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Store - Catégories & Univers',
    'version': '19.0.1.1.0',
    'category': 'Website/Website',
    'summary': 'Catégories produits et pages univers pour Pool Store',
    'description': """
        Module Catégories pour Lolirine Pool Store
        ===========================================
        
        CATÉGORIES PRODUITS E-COMMERCE :
        - Traitement de l'eau (7 sous-catégories)
        - Nettoyage & Robots (5 sous-catégories)
        - Espace Wellness (5 sous-catégories)
        - Équipements & Pièces (9 sous-catégories)
        
        PAGES UNIVERS DYNAMIQUES :
        - Page Boutique avec section "Explorez nos univers"
        - Pages par univers avec sous-catégories
        - Liens générés automatiquement vers catégories e-commerce
        - Support des images de catégories
        
        Contact : +32 497 44 41 46 / info@lolirinepoolstore.be
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/product_categories.xml',
        'views/dynamic_pages.xml',
        'data/website_menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_categories/static/src/css/universes.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
