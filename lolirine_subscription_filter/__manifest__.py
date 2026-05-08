# -*- coding: utf-8 -*-
{
    'name': "Lolirine - Filtrage produits abonnements",
    'summary': "Exclut les produits Pool Store de la recherche produit dans les abonnements Garde-meuble",
    'description': """
Filtre la recherche produit sur le formulaire des abonnements (sale_subscription)
pour ne proposer que les produits Garde-meuble (is_pool_product=False).

Cible : éviter qu'un produit Pool Store (POOL-*) ne soit ajouté par erreur
sur un contrat d'abonnement Garde-meuble.
    """,
    'author': "Rodney Feron - Lolirine SRL",
    'website': "https://www.lolirine.be",
    'category': 'Sales/Subscriptions',
    'version': '19.0.1.0.0',
    'depends': [
        'sale_subscription',
        'lolirine_pool',  # fournit le champ is_pool_product
    ],
    'data': [
        'views/sale_subscription_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
