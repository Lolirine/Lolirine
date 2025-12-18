{
    "name": "Lolirine Scan TVA - Documents Integration",
    "version": "18.0.2.0.0",
    "category": "Accounting/Accounting",
    "summary": "Integration du module Scan TVA avec l'application Documents",
    "description": """
        Module bridge entre Lolirine Scan TVA et l'application Documents.
        
        Fonctionnalites:
        - Archivage automatique des scans dans l'application Documents
        - Creation automatique du dossier "Scans TVA" dans Finance
        - Lien direct vers le document archive depuis le scan
        - Mise a jour du partenaire sur le document lors de la validation
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
