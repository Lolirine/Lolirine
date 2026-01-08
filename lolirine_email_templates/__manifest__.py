# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Templates Email',
    'version': '19.0.1.5.0',
    'category': 'Marketing',
    'summary': 'Templates email personnalisés pour Lolirine Garde-Meubles',
    'description': """
        Module contenant les templates d'emails personnalisés pour Lolirine SPRL:
        - Annonce nouveau portail client (basé sur abonnements)
        - Annonce nouveau portail client (basé sur contacts)
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
        'sale_subscription',
    ],
    'data': [
        'data/email_templates.xml',
        'data/server_actions.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
