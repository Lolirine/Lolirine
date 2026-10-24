{
    'name': 'Lolirine Pool Promotions',
    'version': '19.0.2.0.0',
    'category': 'Website',
    'summary': 'Gestion des promotions hebdomadaires pour Lolirine Pool Store',
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': [
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'views/pool_promotion_views.xml',
        'views/pool_promotion_menu.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
