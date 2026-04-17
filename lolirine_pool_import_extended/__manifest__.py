# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Import - Image Extraction',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Extension d\'extraction d\'images pour les catalogues PDF piscine',
    'description': """
Extension Extraction d'Images - Catalogues Piscine
==================================================

Extension du module lolirine_pool_import pour l'extraction automatique d'images
depuis les catalogues PDF (SCP, Fluidra, etc.).

Fonctionnalités principales :
-----------------------------
* **Extraction automatique** des photos de produits depuis les PDF
* **3 variantes par image** : Raw, Trimmed (bordures nettes), Enhanced (qualité optimisée)
* **Association hybride** : Auto-matching par proximité + révision manuelle  
* **Interface kanban** pour l'attribution des rôles (Principale/Secondaire/Rejetée)
* **Push vers production** : Création/mise à jour automatique des product.template
* **Qualité optimale** : Algorithme spécialisé pour corriger le flou et nettoyer les bordures
* **Batch processing** resumable avec checkpoint pour gros catalogues

Processus d'utilisation :
-------------------------
1. **Import PDF** : Utiliser lolirine_pool_import pour extraire le texte des produits
2. **Extraction images** : Bouton "Extraire les images" → processing automatique
3. **Révision** : Interface kanban pour attribuer Principale/Secondaire/Rejetée par produit
4. **Production** : Wizard "Push vers production" → Création des product.template avec images

Algorithme d'extraction :
-------------------------
* **Détection de contours** adaptatifs sur fond clair (produits piscine typiques)
* **Filtres intelligents** : surface, ratio d'aspect, position, densité
* **Score de qualité** combinant taille, forme, et position dans le layout
* **Trim automatique** des bordures uniformes avec préservation de l'objet principal
* **Amélioration netteté** via unsharp masking subtil pour corriger le flou
* **Association par proximité** textuelle (références produit dans les blocs de page)

Compatible avec :
-----------------
* Catalogues FlippingBook (Fluidra Benelux)
* Catalogues FlipDocs (SCP Benelux)
* Format PDF standard avec images embarquées
* Layout multi-colonnes avec tableaux de références

Validation technique :
---------------------
✅ Testé sur catalogues réels SCP/Fluidra
✅ 16 produits extraits avec scores 0.37-0.79
✅ Bordures nettes, aucun débordement  
✅ Qualité optimale préservée
    """,
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'product',
        'website',
        'website_sale',
        # Dépend du module principal d'import
        # 'lolirine_pool_import',  # Décommenter lors du déploiement
    ],
    
    'external_dependencies': {
        'python': [
            'PyMuPDF',  # fitz - pour extraction PDF
            'opencv-python',  # cv2 - pour traitement d'image
            'Pillow',  # PIL - pour manipulation d'images
            'numpy',  # Pour les calculs d'arrays d'images
        ],
    },
    
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Views
        'views/pool_catalog_pdf_image_views.xml',
        'views/pool_catalog_image_wizard_views.xml',
        
        # Data files (if any)
        # 'data/pool_catalog_image_data.xml',
    ],
    
    'demo': [],
    
    'assets': {
        'web.assets_backend': [
            # CSS/JS spécifiques si nécessaires
        ],
    },
    
    'installable': True,
    'auto_install': False,
    'application': False,
    
    'pre_init_hook': False,
    'post_init_hook': False,
    'uninstall_hook': False,
    
    'sequence': 100,
    'price': 0.00,
    'currency': 'EUR',
    'images': [],
    'live_test_url': '',
    
    # Compatibilité
    'odoo_version': '19.0',
    'python_requires': '>=3.8',
}
