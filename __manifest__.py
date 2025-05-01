{
    'name': 'Box Storage Map',
    'version': '1.0',
    'summary': 'Visualisation interactive des boxes de stockage',
    'category': 'Warehouse',
    'author': 'Erin',
    'depends': ['base', 'web'],
    'data': [
        'views/box_map_template.xml',
        'views/box_stockage_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'box_storage_map/static/src/js/box_map.js',
        ],
    },
    'application': True,
}