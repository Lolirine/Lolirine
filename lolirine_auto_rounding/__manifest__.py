# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Arrondi Automatique',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Applique automatiquement l\'arrondi Euro sur les factures',
    'description': """
        Module pour Lolirine SPRL:
        - Applique automatiquement l'arrondi "Arrondi Euro" sur les nouvelles factures
        - Affiche les prix arrondis sur le portail client
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'sale',
        'sale_subscription',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
