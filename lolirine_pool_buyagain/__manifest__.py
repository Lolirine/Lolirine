{
    'name': 'Lolirine Pool – Acheter à nouveau',
    'version': '19.0.1.0.0',
    'category': 'Lolirine',
    'summary': 'Page "Acheter à nouveau" pour le Pool Store',
    'author': 'Lolirine',
    'license': 'OPL-1',
    'depends': ['website_sale', 'sale'],
    'data': [
        'views/buyagain_page.xml',
        'views/buyagain_menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_buyagain/static/src/css/buyagain.css',
            'lolirine_pool_buyagain/static/src/js/buyagain.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
