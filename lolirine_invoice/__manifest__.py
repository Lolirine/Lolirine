{
    "name": "Lolirine Gestion Factures",
    "version": "19.0.2.0.0",
    "category": "Accounting/Invoicing",
    "summary": "Gestion avancee des factures avec relances, tags, dashboard et export comptable",
    "description": """
        Module de gestion des factures pour Lolirine Garde-Meubles
        
        FONCTIONNALITES PRINCIPALES:
        ============================
        
        Gestion des factures:
        - Rapport PDF personnalise style Lolirine
        - Apercu de la facture sans telechargement
        - Confirmation et envoi en un clic
        - Tags/etiquettes pour classifier les factures
        - Notes internes (non imprimees)
        - Duplication intelligente avec mise a jour des dates
        
        Envoi automatique:
        - Envoi email automatique apres confirmation
        - Integration Peppol complete
        - Configuration par client et par abonnement
        - Envoi groupe de plusieurs factures
        
        Gestion des impayes:
        - Systeme de relances (1er, 2eme, 3eme rappel, mise en demeure)
        - Templates email personnalises pour chaque niveau
        - Calcul automatique des penalites de retard (taux legal belge)
        - Suivi des jours de retard
        - Alertes echeances
        
        Statistiques et dashboard:
        - Tableau de bord CA mensuel
        - Analyse par client
        - Vue pivot et graphiques
        - Export comptable (CSV Standard, Winbooks, BOB)
        
        Configuration Peppol:
        - EAS (Electronic Address Scheme) sur fiche client
        - Endpoint Peppol (numero d'entreprise)
        - Envoi automatique ou manuel
        - Suivi des factures envoyees via Peppol
    """,
    "author": "Lolirine SPRL",
    "license": "LGPL-3",
    "depends": [
        "account",
        "sale_subscription",
        "project_sale_subscription",
        "sale_subscription_partnership",
        "mail",
        "web",
    ],
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Reports
        "report/external_layout_lolirine.xml",
        "report/report_invoice_lolirine.xml",
        # Data
        "data/mail_template.xml",
        "data/reminder_templates.xml",
        "data/default_tags.xml",
        # Wizards (doit etre charge AVANT les menus)
        "wizard/invoice_send_wizard_views.xml",
        "wizard/invoice_wizard_views.xml",
        # Views
        "views/invoice_tag_views.xml",
        "views/invoice_reminder_views.xml",
        "views/invoice_dashboard_views.xml",
        "views/account_move_views.xml",
        # Menus (en dernier)
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [],
    },
    "installable": True,
    "application": True,
    "icon": "/lolirine_invoice/static/description/icon.png",
}
