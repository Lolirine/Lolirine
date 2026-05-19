{
    'name': "Lolirine - Annulation d'attribution bancaire",
    'version': '19.0.1.0.0',
    'summary': "Permet d'annuler facilement l'attribution erronée d'une transaction bancaire",
    'description': """
Lolirine - Annulation d'attribution bancaire
=============================================

Ajoute la possibilité d'annuler proprement l'attribution d'une transaction
bancaire mal réconciliée, avec un wizard de confirmation présentant l'aperçu
des écritures comptables actuelles.

Utilisation :
-------------
Aller dans **Comptabilité > Annuler attribution bancaire**.
Sélectionner une ou plusieurs transactions, puis cliquer sur le menu
**Actions > Annuler l'attribution**.

Le wizard de confirmation s'affiche avec :
  * Détails complets de la transaction (mode unique)
  * Tableau HTML de l'aperçu des écritures comptables actuelles
  * Liste des transactions sélectionnées (mode multiple)

Comportement technique :
------------------------
* Délettre les écritures réconciliées
* Replace la contrepartie sur le compte d'attente du journal
* Retire le partner_id du move et de la bank line
* Trace l'action dans le chatter et les logs
""",
    'author': "Lolirine SRL",
    'website': "https://www.lolirine.be",
    'license': 'LGPL-3',
    'category': 'Accounting/Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/unmatch_wizard_views.xml',
        'views/bank_statement_line_views.xml',
        'data/server_action.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
