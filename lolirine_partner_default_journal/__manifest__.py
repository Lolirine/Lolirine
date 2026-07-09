# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Partner Default Journal',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': "Journal par defaut sur res.partner pour les factures d'achat et de vente",
    'description': """
Restaure et generalise le mecanisme du champ property_purchase_journal_id
qui a ete retire de res.partner en Odoo 19.

Fonctionnalites:
- Ajoute deux champs company-dependent sur res.partner :
    * property_purchase_journal_id  : journal d'achat prefere pour ce fournisseur
    * property_sale_journal_id      : journal de vente prefere pour ce client
- Override _search_default_journal sur account.move pour lire ces champs
  avant le fallback Odoo standard.
- Affiche les 2 champs sur l'onglet Comptabilite de la fiche partenaire.

Cas d'usage principal : router automatiquement les factures d'un fournisseur
specifique vers un journal dedie (ex. T.E.P. -> Achats Piscines).
""",
    'author': 'Lolirine SRL',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'contacts',
    ],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
