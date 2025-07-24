# -*- coding: utf-8 -*-
{
    'name': 'Box de Stockage - Réservation en Ligne',
    'version': '1.1',
    'category': 'Website',
    'summary': 'Ajoute un bouton de réservation pour les boxes libres avec formulaire',
    'author': 'Rodney Feron',
    'website': 'https://www.lolirine.be',
    'depends': ['website_sale', 'website_form'],
    'data': [
        'views/product_template_inherit.xml',
        'views/form_template.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}