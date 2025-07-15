# -*- coding: utf-8 -*-
{
    'name': "Rapport de Contrat de Bail sur Abonnement",
    'summary': "Ajoute un rapport de contrat de bail pour les abonnements d'espaces de stockage.",
    'description': "Ce module intègre un rapport de contrat de bail au module Abonnement d'Odoo.",
    'author': "Votre Nom",
    'website': "https://www.votre-site.com",
    'category': 'Sales/Subscription',
    'version': '1.0',
    'depends': ['sale_subscription'],
    'data': [
        'report/report_contrat_bail.xml',
        'report/template_contrat_bail.xml',
        'views/sale_subscription_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
