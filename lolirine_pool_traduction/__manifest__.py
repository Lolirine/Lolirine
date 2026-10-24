{
    'name': 'Lolirine Pool – Traduction automatique des fiches',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': "Traduit les fiches produits du Pool Store en néerlandais et en anglais "
               "et rédige leurs titres et descriptions Google (API Claude, traitement par lots)",
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/traduction_views.xml',
    ],
    'installable': True,
    'application': False,
}
