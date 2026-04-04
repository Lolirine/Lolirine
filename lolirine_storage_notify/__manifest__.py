{
    'name': 'Lolirine Storage Notify',
    'version': '19.0.1.0.0',
    'category': 'Lolirine',
    'summary': 'Notifications temps réel – Bus.bus, Activités, Web Push (garde-meuble)',
    'author': 'Lolirine',
    'website': 'https://www.lolirine.be',
    'license': 'OPL-1',
    'depends': [
        'base',
        'bus',
        'mail',
        'calendar',
        'portal',
        'website',
        'auth_signup',
        'crm',
    ],
    'data': [
        # 1. Sécurité en premier (toujours)
        'security/ir.model.access.csv',
        # 2. Données de base
        'data/mail_activity_type.xml',
        'data/ir_config_parameter.xml',
        # 3. Wizard EN PREMIER : l'action action_vapid_setup_wizard
        #    doit être créée avant d'être référencée dans res_config_settings_views.xml
        'wizard/vapid_setup_views.xml',
        # 4. Vues (peuvent référencer les actions ci-dessus)
        'views/push_subscription_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'lolirine_storage_notify/static/src/js/notify_service.js',
            'lolirine_storage_notify/static/src/js/push_register_backend.js',
            'lolirine_storage_notify/static/src/xml/notify_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
