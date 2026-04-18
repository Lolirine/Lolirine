# -*- coding: utf-8 -*-
{
    'name': '🖼️ Lolirine Pool Import - Images',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Extension extraction d\'images pour catalogues pool PDF',
    'description': """
🖼️ Lolirine Pool Import - Extension Images
==========================================

Extension du module lolirine_pool_import pour extraire automatiquement
les images des catalogues PDF et les associer aux produits.

Fonctionnalités :
-----------------
* ✅ **Extraction automatique** d'images depuis catalogues SCP/Fluidra
* ✅ **3 variantes par image** : Raw, Trimmed (bordures), Enhanced (netteté)  
* ✅ **Interface intuitive** : Kanban pour attribution Principale/Secondaire/Rejetée
* ✅ **Push vers production** : Création product.template avec images
* ✅ **Version stable** : Utilise PyMuPDF + PIL (pas d'OpenCV)

Workflow :
----------
1. Import PDF via lolirine_pool_import (comme d'habitude)
2. Nouveau bouton "🖼️ Extraire les images" 
3. Processing automatique + association intelligente
4. Révision manuelle via interface kanban
5. Push sélectif vers les fiches produits

Technique :
-----------
* Extraction via images embarquées PDF (très fiable)
* Amélioration qualité : netteté +30%, contraste +10%
* Association par ordre d'apparition sur page
* Compatible Odoo 19, dépendances minimales

Parfait pour vos catalogues SCP et Fluidra ! 🏊‍♂️
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
    ],
    
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 101,
}
