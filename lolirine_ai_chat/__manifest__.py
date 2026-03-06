{
    'name': 'Lolirine AI Chat Assistant',
    'version': '19.0.1.1.0',
    'category': 'Website',
    'summary': 'Assistant IA pour Lolirine Pool Store avec recherche web et catalogue',
    'description': 'Chat IA integre au site web avec Claude AI, recherche produits, sources web et analytics.',
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ai_chat_data.xml',
        'views/ai_chat_views.xml',
        'views/res_config_settings_views.xml',
        'views/ai_chat_menu.xml',
        'views/templates.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
