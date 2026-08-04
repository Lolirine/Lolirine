# -*- coding: utf-8 -*-
{
    'name': 'Lolirine - Factures manquantes',
    'summary': "Detecte les transactions bancaires sans facture correspondante",
    'description': """
Classe les lignes de releve bancaire en six statuts : rapprochee, candidate
trouvee, facture deja soldee, facture manquante, sans facture attendue, non
applicable.

Seul le statut "facture manquante" signale un document reellement absent
(fournisseurs etrangers hors Peppol, factures oubliees). Les remboursements de
credit, la TVA et les virements internes sont exclus via la case "Aucune
facture attendue" des modeles de rapprochement.

Menu : Comptabilite > Fournisseurs > Factures manquantes
""",
    'author': 'Lolirine SRL',
    'category': 'Accounting',
    'version': '19.0.3.0.0',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/statement_line_views.xml',
        'views/journal_dashboard_views.xml',
    ],
    'installable': True,
    'application': False,
}
