{
    'name': 'Lolirine Pool – Wishlist',
    'version': '19.0.1.0.0',
    'category': 'Lolirine',
    'summary': 'Liste de souhaits enrichie pour le Pool Store',
    'author': 'Lolirine',
    'license': 'OPL-1',
    'depends': ['website_sale_wishlist', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'views/wishlist_config_views.xml',
        'views/wishlist_page.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_wishlist/static/src/css/wishlist.css',
            'lolirine_pool_wishlist/static/src/js/wishlist.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
