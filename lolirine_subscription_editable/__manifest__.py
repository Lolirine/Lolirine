# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Abonnements Editables',
    'version': '19.0.2.0.0',
    'category': 'Sales/Subscriptions',
    'summary': 'Permet de modifier le numéro d\'abonnement',
    'description': '''
        Ce module permet de :
        - Modifier le numéro d'abonnement (référence) via un bouton dédié
        - Encoder des abonnements avec des numéros existants
        - Réinitialiser la séquence des abonnements
        - Définir une référence personnalisée lors de la création
    ''',
    'author': 'Lolirine SPRL',
    'license': 'LGPL-3',
    'depends': [
        'sale_subscription',
        'sales_team',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_subscription_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
