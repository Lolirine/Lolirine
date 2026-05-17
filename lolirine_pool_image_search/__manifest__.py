# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Image Search',
    'version': '19.0.1.1.0',
    'category': 'Sales/Sales',
    'summary': 'Recherche web d\'images produits avec validation manuelle',
    'description': """
Lolirine Pool Image Search
==========================

Module de recherche d'images produits via scraping ciblé des sites
fournisseurs (Fluidra, SCP) et marques (Pentair, Hayward, Zodiac, AstralPool,
BWT, etc.) sur base du nom et de la référence produit.

Pipeline
--------
1. **Scraping multi-sources** par ordre de priorité
   - Sites fournisseurs (Fluidra, SCP)
   - Sites marques (recherche par SKU)
   - Recherche site:domain via DuckDuckGo HTML (fallback gratuit)

2. **Filtrage qualité automatique**
   - Résolution minimum 500×500
   - Ratio d'aspect proche de 1:1 (packshot)
   - Exclusion des logos/icônes par hash perceptuel
   - Score de confiance multi-critères

3. **Post-traitement**
   - Background removal automatique (rembg local)
   - Resize 1200×1200 max, conversion WebP
   - Détection doublons via hash perceptuel
   - Auto-validation top-1 si score > 90%

4. **Validation manuelle**
   - Vue kanban avec gestes mobile
   - Tap = image principale
   - Drag = ajouter en galerie
   - Swipe = rejeter

Modèles
-------
* pool.image.search.session : campagne de recherche
* pool.image.search.candidate : candidat image avec score
* pool.image.search.source : registre des sources scrapables

Dépendances Python
------------------
* requests, beautifulsoup4 : scraping HTTP
* Pillow : traitement image
* imagehash : hash perceptuel
* rembg (optionnel) : background removal
    """,
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'product',
        'website',
        'website_sale',
    ],

    'external_dependencies': {
        'python': [
            'requests',
            'bs4',
            'PIL',
            'imagehash',
        ],
    },

    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/pool_image_search_source_data.xml',
        'wizards/launch_search_wizard_views.xml',
        'views/pool_image_search_session_views.xml',
        'views/pool_image_search_candidate_views.xml',
        'views/product_template_views.xml',
        'views/menus.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'lolirine_pool_image_search/static/src/js/candidate_kanban.js',
            'lolirine_pool_image_search/static/src/scss/candidate_kanban.scss',
        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,
}
