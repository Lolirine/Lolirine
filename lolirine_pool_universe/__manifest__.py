{
    'name': "Lolirine — Univers produits (défilés fiche produit, boutique et accueil)",
    'version': '19.0.1.3.0',
    'category': 'Website/eCommerce',
    'summary': "Défilés continus de produits par univers : fiche produit, page boutique et page d'accueil",
    'author': 'Lolirine SRL',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pool_universe_views.xml',
        'views/website_views.xml',
        'views/website_sale_templates.xml',
        'views/home_templates.xml',
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_universe/static/src/scss/pool_universe.scss',
            'lolirine_pool_universe/static/src/js/home_slot.interaction.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
