{
    'name': "Lolirine - Annulation d'attribution bancaire",
    'version': '19.0.1.0.0',
    'summary': "Permet d'annuler facilement l'attribution erronée d'une transaction bancaire",
    'description': """
Lolirine - Annulation d'attribution bancaire
=============================================

Ajoute la possibilité d'annuler proprement l'attribution d'une transaction bancaire
mal réconciliée, avec un wizard de confirmation présentant l'aperçu des écritures
comptables actuelles.

Fonctionnalités :
-----------------
* Bouton "Annuler l'attribution" dans la vue formulaire des transactions bancaires
* Action de masse depuis la vue liste (menu Action)
* Wizard de confirmation avec aperçu détaillé avant exécution
* Délettrage automatique des écritures liées
* Remise en suspense propre pour ré-attribution via le widget de rapprochement
* Trace de l'action dans le chatter
""",
    'author': "Lolirine SRL",
    'website': "https://www.lolirine.be",
    'license': 'LGPL-3',
    'category': 'Accounting/Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/unmatch_wizard_views.xml',
        'views/account_bank_statement_line_views.xml',
        'data/server_action.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
