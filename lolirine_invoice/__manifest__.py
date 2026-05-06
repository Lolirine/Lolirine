{
    "name": "Lolirine Gestion Factures",
    "version': '19.0.2.2.0",
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
        "account_followup",  # Pour personnaliser le rapport de relance
        "sale_subscription",
        "storage_plan_module",
        "project_sale_subscription",  # Pour le patch set_close
        "sale_subscription_partnership",  # Pour le patch set_close
        "mail",
        "web",
    ],
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Reports
        "report/external_layout_lolirine.xml",
        "report/report_invoice_lolirine.xml",
        "report/report_followup_lolirine.xml",
        "report/contract_close_report.xml",
        # Data
        "data/mail_template.xml",
        "data/reminder_templates.xml",
        "data/reminder_cron.xml",
        "data/default_tags.xml",
        # Wizards (doit etre charge AVANT les menus)
        "wizard/invoice_send_wizard_views.xml",
        "wizard/invoice_wizard_views.xml",
        "wizard/lolirine_refund_wizard_views.xml",
        # Views
        "views/invoice_tag_views.xml",
        "views/invoice_reminder_views.xml",
        "views/invoice_dashboard_views.xml",
        "views/account_move_views.xml",
        "views/invoice_audit_wizard_views.xml",
        "views/box_consistency_wizard_views.xml",
        "views/indexation_audit_wizard_views.xml",
        "views/indexation_send_wizard_views.xml",
        "views/contract_close_wizard_views.xml",
        "views/storage_box_views.xml",
        "views/payment_marker_views.xml",
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
