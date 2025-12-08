# -*- coding: utf-8 -*-
{
    'name': 'Visites & Parcours Client',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Gestion des visites et du parcours client pré-contrat pour garde-meubles',
    'description': """
        Module de gestion des visites pour entreprise de self-storage / garde-meubles.
        
        Fonctionnalités :
        - Planification des visites avec créneaux horaires
        - Notifications automatiques (email/SMS) de confirmation et rappel
        - Check-list numérique de visite
        - Signature électronique sur tablette
        - Conversion en devis/abonnement en un clic
        - Pipeline de suivi type mini-CRM
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'calendar',
        'sale_management',
        'sms',
        'web',
    ],
    'data': [
        # Security
        'security/visite_box_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'data/visite_checklist_data.xml',
        # Views
        'views/visite_box_views.xml',
        'views/visite_checklist_views.xml',
        'views/visite_creneau_views.xml',
        'views/res_partner_views.xml',
        'views/storage_box_views.xml',
        'views/visite_box_menus.xml',
        # Wizards
        'wizard/visite_to_quotation_wizard_views.xml',
        # Reports
        'report/visite_report.xml',
        'report/visite_fiche_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'visite_box/static/src/css/visite_box.css',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
