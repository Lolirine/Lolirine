{
    'name': "Lolirine — Univers produits (défilés fiche produit et boutique)",
    'version': '19.0.1.1.0',
    'category': 'Website/eCommerce',
    'summary': "Défilés continus de produits par univers : fiche produit et page boutique",
    'author': 'Lolirine SRL',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pool_universe_views.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_universe/static/src/scss/pool_universe.scss',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
