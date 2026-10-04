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

v6 : montant restant a rapprocher comme cible, tolerance frais carte CBC,
identification du fournisseur par le libelle, case « A reclamer » enregistree,
formulaire de transaction et boutons d'ouverture (transaction, factures,
creation de facture).

Menu : Comptabilite > Fournisseurs > Factures manquantes
""",
    'author': 'Lolirine SRL',
    'category': 'Accounting',
    'version': '19.0.6.0.0',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/res_partner_views.xml',
        'views/statement_line_views.xml',
        'views/journal_dashboard_views.xml',
    ],
    'installable': True,
    'application': False,
}
