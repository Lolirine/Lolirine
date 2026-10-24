{
    'name': 'Lolirine Pool – Retours clients',
    'version': '19.0.1.4.1',
    'category': 'Lolirine',
    'summary': "Parcours de retour façon Amazon : demande depuis l'espace client, règles des CGV, bon de retour PDF avec QR code",
    'description': """
Retours clients du Pool Store
=============================
* Bouton « Retourner ou signaler un problème » sur chaque commande de l'espace client.
* Choix des articles, des quantités, du motif (liste fixe) et ajout de photos.
* Règles des CGV paramétrables : délai de rétractation, articles exclus (sur mesure,
  chimie ouverte), clients professionnels, frais de remise en stock, remboursement
  sans retour sous un seuil, délai de signalement des colis abîmés, garantie
  légale de 2 ans (consommateurs) et garantie fabricant par fournisseur.
* Bon de retour PDF (numéro, QR code, adresse de renvoi, articles) envoyé par e-mail
  et téléchargeable depuis l'espace client.
* Suivi au back-office : Demandé → Accepté → Reçu → Remboursé (avoir brouillon).
""",
    'author': 'Lolirine',
    'license': 'OPL-1',
    'depends': ['website_sale', 'sale_stock', 'portal', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/pool_return_rules.xml',
        'data/pool_return_sequence.xml',
        'report/pool_return_report.xml',
        'data/pool_return_mail.xml',
        'views/pool_return_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
        'views/portal_templates.xml',
        'views/portal_order_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_returns/static/src/css/returns.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
