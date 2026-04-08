# -*- coding: utf-8 -*-
{
    'name': 'Lolirine — CORS Headers',
    'version': '19.0.1.0.0',
    'summary': 'Ajoute les en-têtes CORS pour les appels JSON-RPC externes',
    'description': """
        Permet aux applications externes (artifacts Claude, apps mobiles, etc.)
        d'appeler l'API JSON-RPC de lolirinepoolstore.be sans blocage CORS.
        Autorise uniquement les origines listées dans les paramètres système.
    """,
    'author': 'Lolirine SRL',
    'website': 'https://www.lolirinepoolstore.be',
    'category': 'Technical',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
        'data/ir_config_parameter.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
