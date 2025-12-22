{
    "name": "Lolirine Scan TVA",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Scan et extraction automatique des souches TVA fournisseurs",
    "description": """
        Module de scan et extraction des souches TVA pour Lolirine
        
        Fonctionnalites:
        - Upload de documents
        - Extraction des informations TVA
        - Creation automatique de factures fournisseurs
    """,
    "author": "Lolirine SPRL",
    "license": "LGPL-3",
    "depends": ["account", "base_vat"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/scan_tva_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "lolirine_scan_tva/static/src/css/scan_tva.css",
        ],
    },
    "installable": True,
    "application": True,
    "icon": "/lolirine_scan_tva/static/description/icon.png",
}
