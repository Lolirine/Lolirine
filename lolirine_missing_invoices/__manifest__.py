# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Factures manquantes',
    'summary': "Détecte les transactions bancaires sans facture correspondante dans la base",
    'description': """
Analyse les lignes de relevé bancaire non rapprochées et signale celles pour
lesquelles aucune facture candidate n'existe dans la base (fournisseurs
étrangers hors Peppol, factures oubliées, etc.).

- Menu Comptabilité > Fournisseurs > Factures manquantes
- Compteur sur la carte du journal banque (tableau de bord comptable)
""",
    'author': 'Lolirine SRL',
    'category': 'Accounting',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/statement_line_views.xml',
        'views/journal_dashboard_views.xml',
    ],
    'installable': True,
    'application': False,
}
