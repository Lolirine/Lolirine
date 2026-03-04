{
    'name': 'Lolirine Storage Chat Assistant',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Assistant IA pour Lolirine Garde-Meuble',
    'description': 'Chat IA integre au site garde-meuble avec Claude AI.',
    'author': 'Lolirine SRL',
    'website': 'https://lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/storage_chat_data.xml',
        'views/storage_chat_views.xml',
        'views/res_config_settings_views.xml',
        'views/storage_chat_menu.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
