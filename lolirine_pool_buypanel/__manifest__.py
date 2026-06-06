{
    'name': 'Lolirine Pool – Buy Panel',
    'version': '19.0.1.0.0',
    'category': 'Lolirine',
    'summary': 'Panneau produit enrichi (style Amazon+) pour le Pool Store',
    'author': 'Lolirine',
    'license': 'OPL-1',
    'depends': ['website_sale', 'stock'],
    'data': [
        'views/product_page.xml',
        'views/product_accessories.xml',
        'data/menu_chimie.xml',
        'data/menu_traitement_dosage.xml',
        'data/menu_chauffage.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_buypanel/static/src/css/buypanel.css',
            'lolirine_pool_buypanel/static/src/js/buypanel.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
