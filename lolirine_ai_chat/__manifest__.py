{
    'name': 'Lolirine AI Chat Assistant',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Assistant IA pour Lolirine Pool Store',
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_chat_views.xml',
        'views/res_config_settings_views.xml',
        'views/ai_chat_menu.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_ai_chat/static/src/css/ai_chat_widget.css',
            'lolirine_ai_chat/static/src/js/ai_chat_widget.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
