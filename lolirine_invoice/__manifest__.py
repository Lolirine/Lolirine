{
    "name": "Lolirine Gestion Factures",
    "version": "19.0.1.5.0",
    "category": "Accounting/Invoicing",
    "summary": "Gestion avancee des factures avec relances automatiques, apercu, envoi email et Peppol",
    "description": """
        Module de gestion des factures pour Lolirine Garde-Meubles
        
        Fonctionnalites:
        - Rapport PDF personnalise style Lolirine
        - Apercu de la facture sans telechargement
        - Confirmation de facture brouillon en facture definitive
        - Envoi par email avec template personnalise
        - Envoi automatique apres confirmation (email et/ou Peppol)
        - Integration Peppol complete avec configuration par client
        - Interface simplifiee pour la gestion des factures
        - Option d'envoi auto par client et par abonnement
        - Layout de document personnalise "Lolirine"
        
        Systeme de relances automatiques:
        - 4 niveaux de relance (1er, 2eme, 3eme rappel + mise en demeure)
        - Envoi automatique par email selon delais configurables
        - Frais de rappel (20€) et mise en demeure (50€) automatiques
        - Cron journalier pour traitement automatique
        - Verification automatique des factures payees
        
        Configuration Peppol:
        - EAS (Electronic Address Scheme) sur fiche client
        - Endpoint Peppol (numero d'entreprise)
        - Envoi automatique ou manuel
        - Suivi des factures envoyees via Peppol
    """,
    "author": "Lolirine SPRL",
    "license": "LGPL-3",
    "depends": ["account", "sale_subscription", "mail", "web"],
    "data": [
        "security/ir.model.access.csv",
        "report/external_layout_lolirine.xml",
        "report/report_invoice_lolirine.xml",
        "data/mail_template.xml",
        "data/reminder_templates.xml",
        "wizard/invoice_send_wizard_views.xml",
        "views/account_move_views.xml",
        "views/invoice_reminder_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [],
    },
    "installable": True,
    "application": True,
    "icon": "/lolirine_invoice/static/description/icon.png",
}
