# -*- coding: utf-8 -*-
{
    'name': 'Plan Interactif Garde-Meubles',
    'version': '1.0.48',
    'category': 'Services',
    'summary': 'Gestion interactive des boxes de stockage',
    'description': """
        Module de gestion interactive des boxes de garde-meubles
        ==========================================================
        
        * Plan interactif du rez-de-chaussée et du premier étage
        * Visualisation 3D des boxes
        * Calculateur de volume avec bin packing 3D
        * Gestion des statuts (disponible, occupé, maintenance, etc.)
        * Réservation en ligne
        * Gestion des rendez-vous
        * Export/Import XLSX des boxes
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'depends': ['base', 'website', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'views/storage_box_views.xml',
        'views/storage_floor_views.xml',
        'views/box_reservation_views.xml',
        'views/storage_status_color_views.xml',
        'views/storage_furniture_views.xml',
        'views/website_storage_plan_templates.xml',
        'wizard/storage_box_import_wizard_views.xml',
        'views/menus.xml',
        'data/floor_data.xml',
        'data/status_color_data.xml',
        'data/storage_furniture_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # CSS
            'storage_plan_module/static/src/css/storage_plan.css',
            'storage_plan_module/static/src/css/volume_calculator.css',
            # JS
            'storage_plan_module/static/src/js/storage_plan.js',
            'storage_plan_module/static/src/js/volume_calculator.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
