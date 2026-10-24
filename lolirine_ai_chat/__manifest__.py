{
    'name': 'Lolirine AI Chat Assistant',
    'version': '19.0.1.3.1',
    'category': 'Website',
    'summary': 'Assistant IA pour Lolirine Pool Store avec recherche web et catalogue',
    'description': 'Chat IA integre au site web avec Claude AI, recherche produits, sources web et analytics.',
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ai_chat_data.xml',
        'data/ai_chat_cron.xml',
        'views/ai_chat_views.xml',
        'views/res_config_settings_views.xml',
        'views/ai_chat_menu.xml',
        'views/ai_chat_knowledge_views.xml',
        'views/templates.xml',
        'data/product_question_data.xml',
        'views/product_question_views.xml',
        'views/product_question_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_ai_chat/static/src/css/product_questions.css',
            'lolirine_ai_chat/static/src/js/product_questions.js',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
}
