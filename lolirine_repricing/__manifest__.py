{
    'name': 'Lolirine Pool Store — Repricing',
    'version': '19.0.1.0.0',
    'summary': 'Mise à jour automatique des prix depuis les concurrents web (DataForSEO)',
    'description': """
        Compare les prix des produits piscine avec les marchés FR/BE/NL/DE/LU
        via l'API DataForSEO Google Shopping et met à jour les prix automatiquement.

        Règles :
        - Produit avec prix existant  → meilleur concurrent × 0.99
        - Produit sans prix           → meilleur prix du marché direct
        - Plancher marge 20%          → coût / 0.80
        - Aucun concurrent + sans prix → plancher coût / 0.80 (fallback)
    """,
    'author': 'Lolirine SRL',
    'website': 'https://www.lolirine.be',
    'category': 'eCommerce',
    'license': 'OPL-1',
    'depends': ['product', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/repricing_views.xml',
        'wizard/repricing_wizard_views.xml',
        'views/repricing_menu.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
