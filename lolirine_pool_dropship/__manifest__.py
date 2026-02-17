# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool - Dropshipping & Gestion Fournisseurs',
    'version': '19.0.4.2.0',
    'category': 'Sales/Sales',
    'summary': 'Gestion automatisée des commandes dropshipping avec réductions négociées et optimisation des marges',
    'description': """
Lolirine Pool - Module Dropshipping Intelligent
================================================

Ce module permet de :
- Gérer plusieurs fournisseurs par produit avec leurs conditions tarifaires
- Définir des réductions négociées par fournisseur (ex: 35%, 40%, 52.5%)
- Calculer automatiquement le prix d'achat négocié et la marge
- Sélectionner le meilleur fournisseur selon des critères configurables
- Générer automatiquement les commandes fournisseur en dropshipping (en brouillon)
- Vérifier et ajuster les prix avant envoi au fournisseur
- Envoyer les commandes par email avec case à cocher de confirmation
- Suivre les expéditions et les statuts de livraison
- Analyser les performances par fournisseur

Fonctionnalités principales :
-----------------------------
* Configuration multi-fournisseurs par produit
* Prix catalogue fournisseur + réduction négociée = prix d'achat réel
* Workflow: Commande client → BC fournisseur brouillon → Vérification → Envoi email
* Règles de calcul de marge personnalisables
* Gestion du dropshipping (livraison directe au client final)
* Tableau de bord et reporting avancé
* Traçabilité complète des décisions
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine-pool.be',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'purchase',
        'stock',
        'stock_dropshipping',
        'delivery',
        'website_sale',
        'mail',
        'product',
    ],
    'data': [
        # Security
        'security/dropship_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        # Reports (must load before mail templates that reference them)
        'reports/dropship_report_templates.xml',
        'data/mail_template_data.xml',
        # Views
        'views/dropship_config_views.xml',
        'views/supplier_info_views.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/dropship_decision_log_views.xml',
        'views/dropship_dashboard_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
        # Wizards
        'wizards/supplier_selection_wizard_views.xml',
        'wizards/assign_supplier_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': '_post_init_hook',
    'assets': {
        'web.assets_backend': [
            'lolirine_pool_dropship/static/src/css/dropship_dashboard.css',
        ],
    },
}
