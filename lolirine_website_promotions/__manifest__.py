{
    'name': 'Lolirine Pool Store - Page Promotions',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Page Promotions modulable via le Website Builder avec grille dynamique',
    'description': """
        Ajoute une page Promotions personnalisable via le Website Builder :
        - Blocs predéfinis (cartes promo, bannières, catégories)
        - Grille dynamique des produits en promotion (compare_list_price)
        - Zones de drop libres pour contenu additionnel
        - Snippets custom réutilisables
    """,
    'author': 'Lolirine SRL',
    'website': 'https://www.lolirine.be',
    'depends': [
        'website',
        'website_sale',
    ],
    'data': [
        'views/promotions_page_template.xml',
        'views/promotions_snippets.xml',
        'views/website_menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_website_promotions/static/src/css/promotions.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
