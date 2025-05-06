{
    'name': 'Frais et Pénalités',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Gestion des frais et pénalités liés aux abonnements',
    'license': 'Other proprietary',
    'depends': ['base', 'sale_subscription', 'account'],
    'data': [
        'security/model.xml',
        'security/ir.model.access.csv',
        'views/penalite_views.xml'
    ],
    'installable': True,
    'application': True,
}
