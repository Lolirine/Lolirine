# -*- coding: utf-8 -*-
{
    'name': "Lolirine — SEO & Trafic (Pool Store)",
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': "Suivi des visites, moteurs de recherche, IA et réseaux, "
               "mots-clés Search Console, audit SEO, 404, IndexNow et rapport hebdo",
    'description': """
Suivi du trafic et du référencement du site Lolirine Pool Store
================================================================

* Mesure sans cookie des pages vues et des entrées sur le site, avec la
  source de chaque visite : moteurs de recherche (Google, Bing, Ecosia,
  Qwant, DuckDuckGo...), assistants IA (ChatGPT, Perplexity, Gemini,
  Copilot...), réseaux sociaux, e-mail, publicité, sites référents, direct.
* Attribution des commandes confirmées à la source d'entrée de la visite.
* Import quotidien Google Search Console (requêtes, pages, positions, CTR)
  et rapport d'opportunités SEO (page 2, CTR faible, nouvelles requêtes).
* Journal des pages 404 (visiteurs et robots) avec création de redirection 301.
* Audit SEO hebdomadaire du catalogue et des pages (titres, méta-descriptions,
  doublons, contenu trop court, images, catégories orphelines).
* Soumission IndexNow (Bing, Yandex, Seznam, Naver...) des fiches modifiées.
* Tableau de bord dans Odoo et rapport hebdomadaire par e-mail.
""",
    'author': 'Lolirine SRL',
    'website': 'https://www.lolirinepoolstore.be',
    'license': 'LGPL-3',
    'depends': ['website', 'website_sale', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/seo_hit_views.xml',
        'views/seo_gsc_views.xml',
        'views/seo_notfound_views.xml',
        'views/seo_issue_views.xml',
        'views/seo_dashboard_views.xml',
        'views/seo_config_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lolirine_seo_tracking/static/src/js/seo_beacon.interaction.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
