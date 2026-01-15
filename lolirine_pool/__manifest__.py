# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool - E-commerce Piscine',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Site e-commerce matériel piscine avec import multi-fournisseurs',
    'description': """
Lolirine Pool - Module E-commerce Matériel Piscine
==================================================

Module complet pour la gestion du site piscine.lolirine.be

Fonctionnalités :
-----------------
* Import multi-fournisseurs (Fluidra, SCP Bénélux, Allforpools, etc.)
* Support CSV, API, OCR pour l'import des catalogues
* Thème personnalisé pour le site piscine
* Gestion des catégories produits spécifiques piscine
* Intégration dropshipping

Fournisseurs supportés :
------------------------
* Fluidra (partenaire agréé)
* SCP Bénélux
* Allforpools
* MyPiscine.com
* Extensible à d'autres fournisseurs

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
    ],
    'data': [
        # Security
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
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
