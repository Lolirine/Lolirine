# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Factures manquantes',
    'summary': "Détecte les transactions bancaires sans facture correspondante dans la base",
    'description': """
Analyse les lignes de relevé bancaire et les classe en six statuts : rapprochée,
candidate trouvée, facture déjà soldée, facture manquante, sans facture attendue,
non applicable.

Seul le statut « facture manquante » signale un document réellement absent
(fournisseurs étrangers hors Peppol, factures oubliées). Les remboursements de
crédit, la TVA et les virements internes sont exclus via la case « Aucune facture
attendue » des modèles de rapprochement.

- Menu Comptabilité > Fournisseurs > Factures manquantes
- Compteur sur la carte du journal banque (tableau de bord comptable)
- Action de liste : rapprochement des candidates uniques
""",
    'author': 'Lolirine SRL',
    'category': 'Accounting',
    'version': '19.0.2.0.0',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/account_reconcile_model_views.xml',
        'views/statement_line_views.xml',
        'views/journal_dashboard_views.xml',
    ],
    'installable': True,
    'application': False,
}
