{
    'name': 'Frais et Pénalités',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Gestion des frais et pénalités liés aux abonnements',
    'depends': ['base', 'sale_subscription', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/penalite_views.xml'
    ],
    'installable': True,
    'application': True,
}
