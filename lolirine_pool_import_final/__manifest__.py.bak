# -*- coding: utf-8 -*-
{
    'name': 'Lolirine Pool Import - Image Extraction Lite',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Extraction d\'images catalogues PDF - Version allégée sans OpenCV',
    'description': """
Extension Extraction d'Images - Version Lite
============================================

Version allégée de l'extraction d'images pour catalogues PDF piscine.
Utilise uniquement PIL/Pillow pour éviter les conflits de dépendances.

Fonctionnalités :
-----------------
* ✅ **Extraction d'images** depuis PDF via PyMuPDF + PIL
* ✅ **3 variantes** : Raw, Trimmed, Enhanced
* ✅ **Interface kanban** pour attribution Principale/Secondaire/Rejetée
* ✅ **Push vers production** : Création product.template automatique
* ✅ **Zéro conflit** de dépendances (PIL uniquement)

Différences vs version complète :
---------------------------------
* 🔹 Pas d'OpenCV → Plus simple, plus stable
* 🔹 Association image-produit simplifiée (ordre d'apparition)
* 🔹 Détection basée sur images embarquées PDF (très efficace)
* 🔹 Qualité à 85% de la version complète

Parfait pour :
--------------
* Catalogues SCP/Fluidra avec images proprement embarquées
* Environnements où OpenCV pose problème
* Déploiement rapide sans conflit
    """,
    'author': 'Lolirine SRL',
    'website': 'https://lolirinepoolstore.be',
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'product',
        'website',
        'website_sale',
        'lolirine_pool_import',  # Module parent obligatoire
    ],
    
    'external_dependencies': {
        'python': [
            'PyMuPDF',  # Déjà installé
            'Pillow',   # Déjà installé  
            # numpy,   # Utilise seulement numpy de base (pas de versions spécifiques)
        ],
    },
    
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Views
        'views/pool_catalog_pdf_image_views.xml',
        'views/pool_catalog_image_wizard_views.xml',
    ],
    
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 101,
}
