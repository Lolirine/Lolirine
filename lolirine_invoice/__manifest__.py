{
    "name": "Lolirine Gestion Factures",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Gestion avancee des factures clients Lolirine",
    "description": """
        Module de gestion des factures clients pour Lolirine SPRL
        
        Fonctionnalites:
        - Apercu PDF des factures
        - Envoi par email
        - Support Peppol
    """,
    "author": "Lolirine SPRL",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/res_partner_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
    "icon": "/lolirine_invoice/static/description/icon.png",
}
