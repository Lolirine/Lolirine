{
    'name': 'Lolirine Email Templates',
    'version': '19.0.1.1.0',
    'category': 'Accounting/Invoicing',
    'summary': 'Templates emails + envoi planifié pour Lolirine Garde-Meubles',
    'description': """
        Templates d'emails pour Lolirine
        =================================
        
        **TEMPLATES DISPONIBLES**
        - Facture mensuelle : Email professionnel avec tableau récapitulatif
        - Rappel de paiement : Relance pour factures impayées
        - Confirmation de paiement : Accusé de réception du paiement
        
        **ENVOI PLANIFIÉ** ✨
        - L'envoi se fait à la DATE DE FACTURATION, pas à la confirmation
        - Un cron journalier vérifie les factures à envoyer
        - Possibilité de définir une date d'envoi personnalisée
        - Historique des envois dans le chatter
        
        **FONCTIONNEMENT**
        1. Cocher "Envoi email planifié" sur le client ou l'abonnement
        2. Les factures générées héritent de ce paramètre
        3. À la confirmation, la facture est marquée "En attente d'envoi"
        4. Le cron envoie automatiquement à la date de facturation
        
        Coordonnées :
        - Email : gardemeublelolirine@gmail.com
        - Tél : 0497/44 41 46 - 0498/52 11 31
        - IBAN : BE07 7320 5208 0866 - CBC
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'mail',
        'sale_subscription',
    ],
    'data': [
        'data/mail_templates.xml',
        'data/ir_cron.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'views/sale_subscription_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
