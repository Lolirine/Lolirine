# -*- coding: utf-8 -*-
{
    'name': "API REST pour Gestion de Boîtes de Stockage",
    'summary': "Fournit une API REST pour lier des produits à des boîtes de stockage et gérer leur état.",
    'description': "Ce module crée un nouveau modèle 'Boîte de Stockage' (storage.box) et expose des endpoints REST sécurisés par clé d'API pour interagir avec une application externe.",
    'author': "AI Assistant",
    'website': "https://www.example.com",
    'category': 'Inventory/API',
    'version': '16.0.1.0.0',
    'depends': ['base', 'product', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/storage_box_views.xml',
        'views/res_users_views.xml',
    ],
    'application': True,
    'installable': True,
}
