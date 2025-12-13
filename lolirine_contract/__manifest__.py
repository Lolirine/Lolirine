{
    "name": "Lolirine Contrat Garde-Meubles",
    "version": "18.0.1.0.0",
    "category": "Sales/Subscriptions",
    "summary": "Generation de contrats PDF pour garde-meubles",
    "author": "Lolirine SPRL",
    "license": "LGPL-3",
    "depends": ["sale_subscription", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "report/contract_report.xml",
        "report/contract_template.xml",
        "data/mail_template.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": True,
}
