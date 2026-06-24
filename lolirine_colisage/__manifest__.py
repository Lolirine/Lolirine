{
    'name': "Lolirine — Colisage / Vente par colis",
    'version': '19.0.1.0.0',
    'summary': "Vente par multiples (colisage) : champ produit, contrôle panier et mention sur la fiche",
    'description': """
Vente par colis (colisage)
==========================
Ajoute un champ *Colisage* sur la fiche produit. Lorsqu'il est supérieur à 1 :
- la fiche produit affiche une mention « Vendu par colis de N pièces » ;
- la quantité par défaut et le pas du sélecteur sont calés sur N ;
- toute quantité ajoutée au panier est arrondie au multiple supérieur de N
  (contrôle serveur via le hook ``_verify_updated_quantity`` d'Odoo 19).
""",
    'author': "Lolirine SRL",
    'license': 'LGPL-3',
    'category': 'Website/eCommerce',
    'depends': ['website_sale'],
    'data': [
        'views/product_template_views.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_colisage/static/src/js/colisage.js',
        ],
    },
    'installable': True,
    'application': False,
}
