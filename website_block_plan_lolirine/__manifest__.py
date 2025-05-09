{
    "name": "Website Block - Plan Lolirine",
    "summary": "Ajoute un bloc HTML personnalisé avec le plan des boxes.",
    "version": "1.0",
    "category": "Website",
    "author": "Feron Rodney",
    "license": "OPL-1",
    "website": "https://srl-lolirine.odoo.com",
    "depends": ["website"],
    "data": [
        "views/snippets/snippets.xml",
        "views/snippets/plan_lolirine_snippet.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "website_block_plan_lolirine/static/src/css/plan_lolirine.css"
        ]
    },
    "application": False,
    "auto_install": False
}