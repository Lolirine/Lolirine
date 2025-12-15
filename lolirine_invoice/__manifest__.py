{
    "name": "Lolirine Gestion Factures",
    "version": "18.0.1.3.0",
    "category": "Accounting/Invoicing",
    "summary": "Gestion avancee des factures avec apercu, confirmation et envoi automatique",
    "description": """
        Module de gestion des factures pour Lolirine Garde-Meubles
        
        Fonctionnalites:
        - Rapport PDF personnalise style Lolirine
        - Apercu de la facture sans telechargement
        - Confirmation de facture brouillon en facture definitive
        - Envoi par email avec template personnalise
        - Envoi automatique apres confirmation
        - Envoi via Peppol (si configure)
        - Interface simplifiee pour la gestion des factures
        - Option d'envoi auto par client
        - Layout de document personnalise "Lolirine"
    """,
    "author": "Lolirine SPRL",
    "license": "LGPL-3",
    "depends": ["account", "sale_subscription", "mail", "web"],
    "data": [
        "security/ir.model.access.csv",
        "report/external_layout_lolirine.xml",
        "report/report_invoice_lolirine.xml",
        "data/mail_template.xml",
        "wizard/invoice_send_wizard_views.xml",
        "views/account_move_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [],
    },
    "installable": True,
    "application": True,
    "icon": "/lolirine_invoice/static/description/icon.png",
}
