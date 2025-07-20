# -*- coding: utf-8 -*-
{
    'name': "Bloqueur de Location (Étiquette Loué)",
    'summary': "Empêche l'ajout au panier des produits ayant l'étiquette 'Loué'.",
    'description': """
        Ce module modifie le site web pour cacher le bouton 'Ajouter au panier'
        et afficher un message d'indisponibilité pour les produits (boxes)
        qui sont marqués avec l'étiquette 'Loué'.
    """,
    'author': "Votre Nom (avec l'aide de l'IA)",
    'website': "https://www.votre-site.com",
    'category': 'Website/Sales',
    'version': '1.0',
    'depends': ['website_sale'],
    'data': [
        'views/templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
