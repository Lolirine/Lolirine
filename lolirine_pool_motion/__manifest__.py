# -*- coding: utf-8 -*-
{
    "name": "Lolirine Pool Store — Motion",
    "version": "19.0.1.1.0",
    "category": "Website",
    "summary": "Animations frontend (Motion One) pilotées par la classe Interaction d'Odoo 19",
    "description": """
Socle d'animations pour le Pool Store (website_id=6).

Vague 0 (socle) :
  - reveal au scroll              [data-motion-reveal]
  - apparition en cascade         [data-motion-stagger] / [data-motion-item]
  - compteurs animés              [data-motion-count]
  - retour tactile (press)        .oe_product / [data-motion-press]

Vague 1 (finition perçue) :
  - cascade automatique de la grille boutique   (#products_grid > .oe_product)
  - header rétractable au scroll                (header#top, opt-out possible)
  - bouton retour-en-haut animé                 (injecté site-wide)
  - flyer d'ajout au panier                     (image qui vole vers le panier)

Respecte prefers-reduced-motion, dégrade sans JS, failsafe anti-contenu-masqué.
Moteur : Motion (motion.dev) v12, build UMD local (window.Motion).
""",
    "author": "Lolirine SRL",
    "website": "https://www.lolirinepoolstore.be",
    "license": "LGPL-3",
    "depends": ["website"],
    "data": [
        "views/motion_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            # 1) Lib + boot : scripts classiques, exécutés avant les modules.
            "lolirine_pool_motion/static/src/lib/motion/motion.min.js",
            "lolirine_pool_motion/static/src/js/motion_boot.js",
            # 2) Styles.
            "lolirine_pool_motion/static/src/scss/motion.scss",
            # 3) Helpers + interactions.
            "lolirine_pool_motion/static/src/js/motion_helpers.js",
            "lolirine_pool_motion/static/src/js/reveal.interaction.js",
            "lolirine_pool_motion/static/src/js/stagger.interaction.js",
            "lolirine_pool_motion/static/src/js/count_up.interaction.js",
            "lolirine_pool_motion/static/src/js/press.interaction.js",
            # --- Vague 1 ---
            "lolirine_pool_motion/static/src/js/shop_grid.interaction.js",
            "lolirine_pool_motion/static/src/js/header_scroll.interaction.js",
            "lolirine_pool_motion/static/src/js/back_to_top.interaction.js",
            "lolirine_pool_motion/static/src/js/add_to_cart_flyer.interaction.js",
        ],
    },
    "installable": True,
    "application": False,
}
