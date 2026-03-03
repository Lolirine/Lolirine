{
    'name': 'Lolirine AI Chat Assistant',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Assistant IA intelligent pour Lolirine Pool Store avec recherche web et gestion backend',
    'description': """
        Module d'assistant IA pour le site e-commerce Lolirine Pool Store.
        
        Fonctionnalités:
        - Widget de chat IA sur toutes les pages du site web
        - Recherche web intégrée via l'API Anthropic
        - Expertise piscine, spa et traitement d'eau
        - Historique complet des conversations côté backend
        - Panneau d'administration avec statistiques
        - Configuration centralisée (clé API, prompt système, apparence)
        - Intégration avec le catalogue produits Odoo
    """,
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
        'views/ai_chat_conversation_views.xml',
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
    'images': ['static/description/banner.png'],
}
