{
    'name': 'Lolirine Pool – Avertissement des commandes payées',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Prévient le gérant (OdooBot, e-mail avec les bons fournisseurs, WhatsApp via "
               "CallMeBot entre 8 h et 20 h) quand un client paie une commande du Pool Store",
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': ['website_sale', 'mail', 'lolirine_pool_dropship'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/alerte_views.xml',
    ],
    'installable': True,
    'application': False,
}
