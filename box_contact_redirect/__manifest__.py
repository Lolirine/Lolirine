# -*- coding: utf-8 -*-
{
    'name': 'Box Contact Redirect',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Remplace le bouton ajouter au panier par un bouton contact pour les box disponibles',
    'description': """
        Module personnalisé pour la gestion de garde-meubles
        ======================================================
        
        * Ajoute un champ pour indiquer si un box est disponible
        * Remplace le bouton "Ajouter au panier" par un bouton "Nous contacter" 
          pour les box marqués comme disponibles
        * Redirige vers le formulaire de contact avec les informations du box
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': ['website_sale', 'sale_subscription'],
    'data': [
        'views/product_template_views.xml',
        'views/website_sale_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
