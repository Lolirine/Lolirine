# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Store - Website',
    'version': '19.0.2.0.0',
    'category': 'Website/Website',
    'summary': 'Site e-commerce Lolirine Pool Store - Matériel de piscine',
    'description': """
        Site e-commerce pour la vente de matériel de piscine
        =====================================================
        
        Ce module configure le site web Lolirine Pool Store :
        
        - Configuration du site multi-site
        - Domaine : www.lolirinepoolstore.be
        - Thème personnalisé bleu/piscine
        - Pages : Accueil, À propos
        - Filtrage des produits piscine par site web
        - E-commerce intégré
        - Clients partagés avec le site principal (garde-meubles)
        
        Compatible avec lolirine_pool_import pour l'import des produits.
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://www.lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/website_data.xml',
        'views/website_templates.xml',
        'views/product_template_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_pool_website/static/src/css/pool_theme.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_post_init_hook',
}
