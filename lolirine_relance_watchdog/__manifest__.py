{
    'name': "Lolirine - Surveillance des relances",
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': "Detecte les factures echues passees a la trappe du cron de relance",
    'description': """
Surveillance des relances clients
=================================

Ce module ne relance jamais un client. Il se contente de signaler les factures
echues dont le suivi est incoherent, afin qu'aucune creance ne reste des mois
sans action puis ne declenche brutalement une mise en demeure.

Signaux detectes
----------------
* Facture echue depuis plus de N jours sans aucune relance envoyee depuis l'echeance
* Client sorti du circuit automatique (followup_reminder_type = manual) et jamais repris
* Facture echue alors que l'abonnement du client est encore actif
* Facture de frais de relance impayee (risque de frais generant des frais)

Ergonomie
---------
* Banniere d'alerte en haut de la vue facture
* Colonne "Motif d'alerte" dans la liste des factures
* Filtre "Relances oubliees" dans la recherche
* Menu Comptabilite > Clients > Relances oubliees
* Cron quotidien de recalcul a 07h00

Parametre systeme
-----------------
``lolirine_relance.alert_days`` : nombre de jours de retard avant alerte (defaut 10)
""",
    'author': "Lolirine SRL",
    'depends': ['account', 'account_followup', 'sale_subscription'],
    'data': [
        'data/ir_cron.xml',
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
