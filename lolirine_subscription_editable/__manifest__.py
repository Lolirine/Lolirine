# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Abonnements Editables',
    'version': '19.0.1.0.0',
    'category': 'Sales/Subscriptions',
    'summary': 'Permet de modifier le numéro d\'abonnement',
    'description': '''
        Ce module permet de :
        - Modifier le numéro d'abonnement (référence)
        - Encoder des abonnements avec des numéros existants
        - Réinitialiser la séquence des abonnements
    ''',
    'author': 'Lolirine SPRL',
    'license': 'LGPL-3',
    'depends': [
        'sale_subscription',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_subscription_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
