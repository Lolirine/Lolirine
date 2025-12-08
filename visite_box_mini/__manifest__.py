# -*- coding: utf-8 -*-
{
    'name': 'Visites Box (Mini)',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Gestion des visites - Version minimale',
    'author': 'Lolirine SPRL',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/visite_box_views.xml',
    ],
    'installable': True,
    'application': True,
}
