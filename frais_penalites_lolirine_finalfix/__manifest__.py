{
    'name': 'Frais et Pénalités',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Gestion des frais et pénalités liés aux abonnements',
    'license': 'Other proprietary',
    'depends': ['base', 'sale_subscription', 'account'],
    'data': [
        'views/penalite_views.xml',
        'security/access_rights.xml'
    ],
    'installable': True,
    'application': True,
}
