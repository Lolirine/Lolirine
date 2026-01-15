# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool - Matériel Piscine',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Gestion du catalogue et ventes de matériel piscine',
    'description': """
Lolirine Pool - Module de gestion piscine
=========================================

Module complet pour la gestion d'un e-commerce de matériel piscine.

Fonctionnalités :
-----------------
* Gestion des fournisseurs spécialisés piscine
* Import multi-méthodes (CSV, API, OCR)
* Mapping intelligent des colonnes
* Calcul automatique des marges
* Catégories produits piscine
* Gestion des marques
* Thème dédié pour le site piscine
* Intégration dropshipping

Fournisseurs supportés :
------------------------
* Fluidra (AstralPool, Zodiac)
* SCP Bénélux
* Allforpools
* MyPiscine.com
* Extensible à d'autres fournisseurs

Compatible Odoo 19.0
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://piscine.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
        'sale',
        'purchase',
        'website',
        'website_sale',
        'website_sale_stock',
        'mail',
    ],
    'data': [
        # Security - IMPORTANT: charger en premier
        'security/pool_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/product_category_data.xml',
        'data/supplier_data.xml',
        'data/website_data.xml',
        # Views
        'views/pool_supplier_views.xml',
        'views/pool_import_views.xml',
        'views/pool_product_views.xml',
        'views/pool_menus.xml',
        # Wizards
        'wizard/pool_import_wizard_views.xml',
        # Website
        'views/website_templates.xml',
        'views/website_snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool/static/src/css/pool_theme.css',
            'lolirine_pool/static/src/js/pool_shop.js',
        ],
        'web.assets_backend': [
            'lolirine_pool/static/src/css/pool_backend.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
