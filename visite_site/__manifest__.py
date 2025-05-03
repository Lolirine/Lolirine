{
    'name': 'Visite du site',
    'version': '1.0',
    'category': 'Garde-Meubles',
    'summary': 'Gestion des visites du site avant location',
    'author': 'Erin',
    'depends': ['base'],
    'data': [
        'views/visite_site_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
