{
    "name": "Lolirine Scan TVA",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Scan et extraction automatique des souches TVA fournisseurs",
    "description": """
        Module de scan et extraction des souches TVA pour Lolirine
        
        Fonctionnalites:
        - Scan ou upload d'images de tickets/factures fournisseurs
        - Visualisation en direct du document scanne
        - Extraction OCR automatique des informations:
            * Numero de TVA du fournisseur
            * Nom et adresse du fournisseur
            * Date de la facture
            * Montants HT, TVA, TTC
            * Numero de facture/ticket
        - Creation automatique du fournisseur s'il n'existe pas
        - Generation de la facture fournisseur
        - Integration complete dans la comptabilite
        - Attribution automatique du compte fournisseur
        - Historique des scans avec pieces jointes
        
        Note: Pour l'OCR automatique, installez pytesseract et Pillow sur le serveur.
        Sans ces bibliotheques, l'extraction manuelle reste disponible.
    """,
    "author": "Lolirine SPRL",
    "license": "LGPL-3",
    "depends": ["account", "mail", "base_vat"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/account_data.xml",
        "wizard/scan_wizard_views.xml",
        "views/scan_tva_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [],
    },
    "installable": True,
    "application": True,
    "icon": "/lolirine_scan_tva/static/description/icon.png",
}
