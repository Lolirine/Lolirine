{
    'name': 'Trajets Interventions',
    'version': '1.0',
    'category': 'Garde-Meubles',
    'summary': 'Enregistrement des trajets liés aux interventions ou livraisons',
    'author': 'Erin',
    'depends': ['base'],
    'data': [
        'views/trajet_intervention_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
