# -*- coding: utf-8 -*-
{
    'name': 'Storage Indexation',
    'version': '18.0.1.0.0',
    'category': 'Services/Storage',
    'summary': 'Indexation automatique des prix de garde-meubles basée sur l\'indice santé belge',
    'description': """
Storage Indexation - Module d'indexation automatique
=====================================================

Ce module permet de gérer l'indexation automatique des prix des abonnements 
de garde-meubles basée sur l'indice santé belge ou d'autres indices.

Fonctionnalités principales:
----------------------------
* Récupération automatique de l'indice santé belge (Statbel)
* Calcul automatique des nouveaux prix indexés
* Mise à jour des lignes d'abonnement
* Génération de documents PDF d'indexation pour les clients
* Notifications automatiques par email
* Historique complet des indexations
* Actions planifiées (CRON) pour l'automatisation

Formule d'indexation belge:
---------------------------
Nouveau loyer = Loyer de base × (Nouvel indice / Indice de base)

Compatibilité:
--------------
* Odoo 18
* Odoo 19 (préparé)
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'sale_subscription',  # Module d'abonnement Odoo 18+
        'contacts',
    ],
    'data': [
        # Sécurité
        'security/storage_indexation_security.xml',
        'security/ir.model.access.csv',
        # Données
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        # Vues
        'views/storage_price_index_views.xml',
        'views/storage_indexation_views.xml',
        'views/sale_subscription_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
        # Wizards
        'wizard/storage_indexation_wizard_views.xml',
        # Rapports
        'report/indexation_report.xml',
        'report/indexation_report_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
