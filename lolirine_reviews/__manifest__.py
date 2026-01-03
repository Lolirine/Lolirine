{
    'name': 'Lolirine - Avis Clients Google',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Bloc carousel pour afficher les avis Google clients',
    'description': """
        Module ajoutant un snippet/bloc pour afficher les avis clients Google
        sur le site web Lolirine avec la charte graphique officielle.
        
        Fonctionnalités:
        - Carousel d'avis clients avec navigation
        - Badge Local Guide Google
        - Note globale avec étoiles
        - Statistiques (22 avis, 100% recommandent, etc.)
        - Design responsive
        - Lien vers Google Maps
        - Bouton CTA vers page contact
        
        Couleurs Lolirine:
        - Principal: #C91E18
        - Hover: #ab1a14
        - Active: #a11813
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_reviews/static/src/scss/reviews.scss',
            'lolirine_reviews/static/src/js/reviews.js',
        ],
    },
    'images': [
        'static/description/banner.svg',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
