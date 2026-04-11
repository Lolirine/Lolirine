# -*- coding: utf-8 -*-
{
    'name': 'Lolirine — Fiche de visite piscine',
    'version': '19.0.3.0.0',
    'summary': 'Fiche de visite chantier piscine — persistance, photos, signature, devis Pool Store',
    'author': 'Lolirine SRL',
    'website': 'https://www.lolirinepoolstore.be',
    'category': 'Website',
    'license': 'LGPL-3',
    'depends': ['website', 'website_sale', 'product', 'sale', 'contacts', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/report_model_views.xml',
        'views/pool_quote_views.xml',
        'views/templates.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
