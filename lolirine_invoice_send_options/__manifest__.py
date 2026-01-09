# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Options Envoi Factures',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Affiche les options d\'envoi (Email/Peppol) sur les factures',
    'description': """
        Module pour Lolirine SPRL:
        - Affiche les checkboxes d'envoi automatique visibles sur la facture
        - Envoi Email et Envoi Peppol avec libellés clairs
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
