{
    'name': 'Lolirine Pool Store - Website',
    'version': '19.0.2.0.0',
    'category': 'Website/Website',
    'summary': 'Site e-commerce Lolirine Pool Store - Matériel de piscine',
    'description': """
        Site e-commerce pour la vente de matériel de piscine
        =====================================================
        
        Ce module crée et configure le site web Lolirine Pool Store :
        
        - Création du 2ème site web (multi-site)
        - Domaine : www.lolirinepoolstore.be
        - Thème personnalisé bleu/piscine
        - Filtrage des produits par site web
        - E-commerce intégré
        - Clients partagés avec le site principal
        
        Contact :
        - Téléphone : +32 497 44 41 46
        - Email : info@lolirinepoolstore.be
        
        Compatible avec lolirine_pool_import pour l'import des produits.
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/website_templates.xml',
        'data/website_data.xml',
        'data/product_category_data.xml',
        'data/website_menu_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_website/static/src/css/pool_theme.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
