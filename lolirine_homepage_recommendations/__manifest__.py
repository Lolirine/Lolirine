# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool - Homepage Recommendations',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Sections de recommandations personnalisées style Amazon pour Lolirine Pool',
    'description': """
        Module de recommandations personnalisées pour Lolirine Pool
        ===========================================================
        
        ⚠️ CE MODULE EST EXCLUSIVEMENT POUR LE SITE LOLIRINE POOL
        
        Ce module ajoute des sections dynamiques à la page d'accueil inspirées d'Amazon:
        
        * Produits récemment consultés
        * Continuez vos achats (basé sur l'historique)
        * Produits populaires dans vos catégories préférées
        * Meilleures ventes
        * Produits les mieux notés
        * Offres et promotions du moment
        * Produits fréquemment achetés ensemble
        * Nouveautés dans vos catégories
        
        Fonctionnalités:
        ----------------
        * Tracking de l'activité visiteur (produits vus, catégories)
        * Algorithme de recommandation basé sur le comportement
        * Snippets configurables pour le Website Builder
        * Carrousels dynamiques avec lazy loading
        * Compatible avec les visiteurs anonymes et connectés
        * Filtré exclusivement pour le site Lolirine Pool
        
        Configuration:
        --------------
        Après installation, allez dans Configuration > Technique > Paramètres système
        et définissez 'lolirine_pool.website_id' avec l'ID du site Lolirine Pool.
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'website_sale',
        'website_sale_wishlist',
        'sale',
        'product',
        'rating',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron_data.xml',
        'views/snippets/homepage_recommendations.xml',
        'views/website_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_homepage_recommendations/static/src/scss/homepage_recommendations.scss',
            'lolirine_homepage_recommendations/static/src/js/homepage_recommendations.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
