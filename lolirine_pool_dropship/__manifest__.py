# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Dropshipping',
    'version': '19.0.3.0.0',
    'category': 'Sales',
    'summary': 'Gestion du dropshipping pour Lolirine Pool Store',
    'description': """
        Module de gestion du dropshipping pour le site e-commerce piscine.
        - Gestion des fournisseurs dropship avec réductions négociées
        - Création de bons de commande fournisseur depuis les commandes clients
        - Dashboard des commandes à traiter
        - Attribution en masse des fournisseurs
    """,
    'author': 'Lolirine SRL',
    'website': 'https://www.lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'purchase',
        'website_sale',
        'product',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Views
        'views/dropship_config_views.xml',
        'views/supplier_info_views.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/dropship_decision_log_views.xml',
        # Wizards
        'wizards/assign_supplier_wizard_views.xml',
        # Menus (must be last)
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
