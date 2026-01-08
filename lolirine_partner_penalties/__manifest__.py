# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Partner Penalties',
    'version': '19.0.1.0.1',
    'category': 'Sales',
    'summary': 'Gestion des pénalités et frais clients pour garde-meubles',
    'description': """
Lolirine Partner Penalties
==========================
Module de gestion des pénalités et frais pour les clients de garde-meubles.

Fonctionnalités:
----------------
* Produit/Box associé au client
* Gestion des pénalités par catégorie :
  - Frais liés aux retards et manquements financiers
  - Frais liés au non-respect du règlement intérieur
  - Frais liés à la dégradation ou à l'état du box
  - Frais liés à l'usage interdit ou dangereux
  - Frais contractuels et juridiques
* Remarques sur le comportement du client
* Historique des pénalités appliquées

Auteur: Lolirine SPRL
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'product',
        'sale_subscription',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/penalty_types.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/partner_penalty_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
