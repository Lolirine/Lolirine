# -*- coding: utf-8 -*-
{
    'name': "API REST pour Gestion de Boîtes de Stockage",
    'summary': """
        Fournit une API REST pour lier des produits à des boîtes de stockage
        et gérer leur état (couleur, disponibilité).""",
    'description': """
        Ce module crée un nouveau modèle 'Boîte de Stockage' (storage.box) et expose des endpoints REST sécurisés par clé d'API pour interagir avec une application externe.
        Endpoints disponibles :
        - GET /api/storage/boxes : Lister toutes les boîtes.
        - GET /api/storage/box/<int:box_id> : Obtenir les détails d'une boîte.
        - PUT /api/storage/box/<int:box_id> : Mettre à jour l'état d'une boîte (ex: l'occuper avec un produit).
    """,
    'author': "Votre Nom",
    'website': "https://www.votre-site.com",
    'category': 'Uncategorized',
    'version': '16.0.1.0.0', # Adaptez à votre version d'Odoo
    'depends': ['base', 'product', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/storage_box_views.xml',
        'views/res_users_views.xml',
    ],
    'application': True,
    'installable': True,
}
