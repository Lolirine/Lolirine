# -*- coding: utf-8 -*-
{
    'name': 'Pool Import Images - Extraction Lite',
    'version': '1.0.0',
    'category': 'Tools',
    'summary': 'Extraction d\'images des catalogues PDF - Version allégée sans OpenCV',
    'description': """
Pool Import Images - Extraction Lite
===================================

Extension du module lolirine_pool_import pour extraire automatiquement
les images des catalogues PDF et les associer aux produits.

Version Lite : Utilise uniquement PIL/Pillow pour éviter les conflits
de dépendances avec d'autres modules.

Fonctionnalités :
- Extraction automatique d'images embarquées des PDF
- 3 variantes par image (brute, détourée, optimisée)  
- Association intelligente images ↔ produits
- Interface de révision (Principale/Secondaire/Rejetée)
- Score de qualité et confiance automatiques
- Compatible Odoo 19 Enterprise

Dépendances :
- lolirine_pool_import
- PyMuPDF (fitz)
- PIL/Pillow
""",
    'author': 'Lolirine SRL',
    'website': 'https://lolirine.be',
    'depends': [
        'base',
        'lolirine_pool_import'
    ],
    'external_dependencies': {
        'python': ['fitz', 'PIL', 'numpy']
    },
    'data': [
        'security/ir.model.access.csv',
        'views/pool_catalog_pdf_image_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    'sequence': 100,
}
