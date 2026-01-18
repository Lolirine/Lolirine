{
    'name': 'Lolirine Email Templates',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Invoicing',
    'summary': 'Templates emails personnalisés pour Lolirine Garde-Meubles',
    'description': """
        Templates d'emails pour Lolirine
        =================================
        
        Ce module contient uniquement les templates d'emails :
        
        - **Facture mensuelle** : Email professionnel avec tableau récapitulatif
        - **Rappel de paiement** : Relance pour factures impayées
        - **Confirmation de paiement** : Accusé de réception du paiement
        
        Coordonnées incluses :
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
    ],
    'data': [
        'data/mail_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
