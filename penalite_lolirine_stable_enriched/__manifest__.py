{
    'name': 'Pénalités Clients',
    'version': '1.0',
    'summary': 'Gestion des pénalités de retard ou d’infraction pour les clients.',
    'description': """Ce module permet de créer, suivre et gérer les pénalités appliquées aux clients
dans le cadre de la location de boxes de stockage.""",
    'author': 'Feron Rodney',
    'website': 'https://www.lolirine.be',
    'category': 'Garde-Meubles',
    'depends': ['base', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],
}
