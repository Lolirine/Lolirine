# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Notes Alert',
    'version': '19.0.1.0.0',
    'category': 'Customizations',
    'summary': "Bandeau d'alerte quand un client ou un abonnement a une note importante",
    'description': """
Affiche un bandeau d'alerte jaune en haut de la fiche partenaire
et de la fiche abonnement (sale.order) lorsqu'une note interne
non vide est presente.

Champs surveilles :
- res.partner.comment (onglet Notes du contact)
- sale.order.internal_note (onglet Note interne de l'abonnement)
""",
    'author': 'Lolirine SRL',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'sale_subscription',
    ],
    'data': [
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
