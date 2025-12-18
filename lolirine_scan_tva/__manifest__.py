{
    "name": "Lolirine Scan TVA",
    "version": "18.0.2.0.0",
    "category": "Accounting/Accounting",
    "summary": "Scan et extraction automatique des souches TVA fournisseurs",
    "description": """
        Module de scan et extraction des souches TVA pour Lolirine
        
        Version 2.0 - Améliorations OCR:
        - Prétraitement d'image (contraste, binarisation)
        - Support amélioré des tickets de supermarché
        - Détection automatique du type de document
        - Meilleure extraction des numéros TVA belges
        - Distinction fournisseur/client sur les tickets
        
        Fonctionnalités:
        - Scan ou upload d'images/PDF de tickets et factures
        - Extraction OCR automatique optimisée
        - Création automatique du fournisseur
        - Génération de la facture fournisseur
        - Intégration comptable complète
    """,
    "author": "Lolirine SPRL",
    "license": "LGPL-3",
    "depends": ["account", "mail", "base_vat"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "wizard/scan_wizard_views.xml",
        "views/scan_tva_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
    "icon": "/lolirine_scan_tva/static/description/icon.png",
}
