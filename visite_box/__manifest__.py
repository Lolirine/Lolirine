# -*- coding: utf-8 -*-
{
    'name': "Visites de Box - Lolirine",
    'summary': "Gestion des rendez-vous de visite pour les boxes de stockage",
    'description': """
        Ce module permet de gérer les visites de clients intéressés par la location de boxes de stockage.
        Il inclut la planification, confirmation, signature sur tablette et suivi des visites.
        Un email est envoyé automatiquement à la confirmation avec un lien Calendly.
    """,
    'author': "Feron Rodney",
    'website': "https://lolirine-lolirine.odoo.com",
    'category': 'Operations/Logistics',
    'version': '1.0',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/visite_box_views.xml',
        'views/visite_box_menus.xml',
        'data/mail_template_visite.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'Proprietary',
}
