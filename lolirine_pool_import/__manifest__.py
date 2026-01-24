{
    'name': 'Lolirine Pool Import - Fluidra',
    'version': '19.0.4.4.0',
    'category': 'Sales/Sales',
    'summary': 'Import produits piscine complet - OCR IA avec création automatique des catégories',
    'description': """
        Module d'import pour catalogues piscine (Fluidra, etc.)
        =======================================================
        
        **LA BOUTIQUE PISCINE LA PLUS COMPLÈTE** 🏊
        
        **EXTRACTION OCR INTELLIGENTE**
        - Détection automatique de 60+ catégories de produits
        - Extraction des spécifications adaptées au type de produit
        - Support des produits simples, variantes et tableaux
        - Recherche d'images Google automatique
        
        **CRÉATION AUTOMATIQUE DES CATÉGORIES E-COMMERCE** ✨ NOUVEAU
        - Détection de la catégorie depuis le catalogue
        - Création automatique de la catégorie parente si inexistante
        - Création automatique de la sous-catégorie si inexistante
        - Hiérarchie complète préservée
        - Assignation automatique du produit
        
        **CATÉGORIES SUPPORTÉES**
        
        🔥 CHAUFFAGE
        - Pompes à chaleur, Réchauffeurs électriques, Échangeurs thermiques
        
        💧 POMPES
        - Pompes de filtration, Nage contre-courant, Pompes doseuses
        
        🧹 FILTRATION
        - Filtres à sable/verre/cartouche/diatomée, Média filtrant
        
        🤖 ROBOTS
        - Robots électriques/hydrauliques/à pression, Nettoyage manuel
        
        ⚗️ TRAITEMENT EAU
        - Électrolyseurs, Régulateurs pH/Chlore, UV, Ozone, Chimie
        
        💡 ÉCLAIRAGE
        - Projecteurs LED, Ampoules, Transformateurs, Boîtes connexion
        
        🏗️ CONSTRUCTION
        - Blocs polystyrène, Margelles, Dalles, Débordement
        
        🔧 PIÈCES À SCELLER
        - Skimmers, Buses, Bondes, Prises balai, Traverses paroi
        
        🔩 TUYAUTERIE & PLOMBERIE
        - Tuyaux PVC, Raccords, Vannes, Clapets, Colles
        
        🛡️ ÉTANCHÉITÉ
        - Liners (armé, étang), Accrochage, Feutre géotextile
        
        🛡️ SÉCURITÉ
        - Alarmes, Barrières, Couvertures
        
        🪜 ACCESSOIRES
        - Échelles, Plongeoirs, Douches, Pédiluves
        
        🌊 WELLNESS
        - Spas gonflables/encastrables, Saunas, Hammams
        
        ⚡ LOCAL TECHNIQUE
        - Coffrets électriques, Tableaux de commande
        
        **PUBLICATION AUTOMATIQUE**
        - Assignation au website Pool Store
        - Catégories e-commerce créées automatiquement
        - Description HTML avec tableau specs
        
        Compatible avec tous catalogues fournisseurs piscine.
    """,
    'author': 'Lolirine SPRL',
    'website': 'https://lolirine.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'sale',
        'purchase',
        'stock',
        'website',
        'website_sale',
        # 'lolirine_pool_dropship' est optionnel - intégration automatique si installé
    ],
    'external_dependencies': {
        'python': ['PIL'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/product_category_data.xml',
        'data/product_attribute_data.xml',
        'wizard/pool_import_wizard_views.xml',
        'views/pool_supplier_views.xml',
        'views/pool_catalog_views.xml',
        'views/pool_catalog_extraction_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'lolirine_pool_import/static/src/css/catalog_extractor.css',
            'lolirine_pool_import/static/src/js/catalog_extractor.js',
            'lolirine_pool_import/static/src/xml/catalog_extractor.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
