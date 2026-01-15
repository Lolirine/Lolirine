{
    'name': 'Lolirine Pool Import - Fluidra',
    'version': '19.0.1.1.0',
    'category': 'Sales/Sales',
    'summary': 'Import de produits Fluidra avec gestion automatique des attributs et variantes',
    'description': """
        Module d'import pour le catalogue Fluidra Benelux
        =================================================
        
        Fonctionnalités:
        - Import CSV/JSON depuis l'extracteur Fluidra
        - Création automatique des attributs de produits
        - Génération des variantes de produits
        - Support multilingue FR/NL
        - Calcul automatique des prix de vente
        - Mapping des catégories Fluidra vers Odoo
        
        Compatible avec l'extracteur React Fluidra Benelux 2026.
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'sale',
        'purchase',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/product_category_data.xml',
        'data/product_attribute_data.xml',
        'wizard/pool_import_wizard_views.xml',
        'views/pool_supplier_views.xml',
        'views/pool_catalog_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'lolirine_pool_import/static/src/css/catalog_extractor.css',
            'lolirine_pool_import/static/src/js/catalog_extractor.js',
            'lolirine_pool_import/static/src/xml/catalog_extractor.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
