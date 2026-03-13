{
    'name': 'Lolirine - Prorata Facturation',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Wizard de calcul de prorata sur les factures de contrat',
    'author': 'Lolirine',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/prorata_wizard_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
