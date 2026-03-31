{
    'name': 'Lolirine Pool Store - Website',
    'version': '19.0.1.0.6',
    'category': 'Website/Website',
    'summary': 'Site e-commerce Lolirine Pool Store - Matériel de piscine',
    'description': """
        Site e-commerce pour la vente de matériel de piscine
        =====================================================
        
        Ce module crée et configure le site web Lolirine Pool Store :
        
        - Création du 2ème site web (multi-site)
        - Domaine : lolirine-pool.be
        - Thème personnalisé bleu/piscine
        - Filtrage des produits par site web
        - E-commerce intégré
        - Clients partagés avec le site principal
        
        Compatible avec lolirine_pool_import pour l'import des produits.
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://lolirine-pool.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'product',
        'lolirine_pool_import',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/brands_page.xml',
        'views/website_templates.xml',
        'data/website_data.xml',
        'data/product_category_data.xml',
        'data/website_menu_data.xml',
        'views/snippets/pool_guides_snippet.xml',
        'views/guides/guide_article_layout.xml',
        'views/guides/guide_pages.xml',
        'views/guides/guide_pages_content.xml',
        'views/snippets/promo_cards_snippet.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_website/static/src/css/pool_theme.css',
            'lolirine_pool_website/static/src/css/brands.css',
            'lolirine_pool_website/static/src/scss/pool_guides.css',
            'lolirine_pool_website/static/src/scss/guide_article.css',
            'lolirine_pool_website/static/src/js/pool_guides.js',
            'lolirine_pool_website/static/src/scss/promo_cards.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
