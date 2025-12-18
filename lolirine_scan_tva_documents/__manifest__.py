{
    "name": "Lolirine Scan TVA - Documents Integration",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Intégration du module Scan TVA avec l'application Documents",
    "description": """
        Module bridge pour intégrer Lolirine Scan TVA avec l'application Documents.
        
        Fonctionnalités:
        - Archivage automatique des scans dans l'application Documents
        - Création automatique du dossier "Scans TVA" dans Finance
        - Lien direct vers le document archivé depuis le scan
        - Mise à jour du partenaire sur le document lors de la validation
    """,
    "author": "Lolirine SPRL",
    "license": "LGPL-3",
    "depends": ["lolirine_scan_tva", "documents"],
    "data": [
        "views/scan_tva_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
