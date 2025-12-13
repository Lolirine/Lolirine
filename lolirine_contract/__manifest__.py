# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Contrat Garde-Meubles',
    'version': '18.0.1.0.0',
    'category': 'Sales/Subscriptions',
    'summary': 'Génération automatique de contrats de location de box garde-meubles',
    'description': """
Lolirine Contrat Garde-Meubles
==============================

Module de génération de contrats PDF pour la location de box de garde-meubles.

Fonctionnalités:
----------------
* Rapport PDF du contrat de location basé sur le modèle Lolirine
* Modèle d'email avec le contrat en pièce jointe
* Envoi automatique du contrat à la confirmation de l'abonnement
* Champs personnalisés pour le code d'accès et code gerbeur

Configuration:
--------------
1. Les contrats sont générés automatiquement depuis les abonnements
2. Le PDF reprend toutes les informations du client et du box loué
3. L'envoi peut être manuel ou automatique à la confirmation

Auteur: Lolirine SPRL
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'sale_subscription',
        'sale_management',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/contract_report.xml',
        'report/contract_template.xml',
        'data/mail_template.xml',
        'data/automation.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {},
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
