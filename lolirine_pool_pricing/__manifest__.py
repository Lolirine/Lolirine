{
    'name': "Lolirine — Tarification SCP",
    'summary': "Lettre tarifaire SCP, prix catalogue, coût, marge et prix de vente",
    'description': """
Tarification des produits du Pool Store à partir du catalogue SCP
=================================================================

Chaque fiche porte son **prix catalogue** et sa **lettre tarifaire**. Le module
en déduit :

* le **coût d'achat**, catalogue × coefficient de la lettre ;
* le **prix de vente**, catalogue × coefficient de vente (0,95 par défaut) ;
* la **marge** en euros et en pourcentage.

Le coefficient de vente se baisse fiche par fiche pour une promotion, et la
marge affichée indique immédiatement si l'opération reste rentable.

Remises SCP appliquées : A 52,5 %, B 33,5 %, C 43 %, D 38 %, E 25 %, F 30 %,
P 50 %.
""",
    'author': "Lolirine SRL",
    'website': "https://www.lolirinepoolstore.be",
    'category': 'Sales/Sales',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['product', 'sale'],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
