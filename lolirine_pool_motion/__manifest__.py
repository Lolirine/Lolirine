# -*- coding: utf-8 -*-
{
    "name": "Lolirine Pool Store — Motion",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Animations frontend (Motion One) pilotées par la classe Interaction d'Odoo 19",
    "description": """
Socle d'animations pour le Pool Store (website_id=6).

Fournit, via la classe Interaction d'Odoo 19 :
  - reveal au scroll              [data-motion-reveal]
  - apparition en cascade         [data-motion-stagger] / [data-motion-item]
  - compteurs animés              [data-motion-count]
  - retour tactile (press)        .oe_product / [data-motion-press]

Respecte prefers-reduced-motion, dégrade proprement sans JS,
et inclut un failsafe anti-contenu-masqué.

Moteur : Motion (motion.dev) v12, build UMD vendu localement (window.Motion).
""",
    "author": "Lolirine SRL",
    "website": "https://www.lolirinepoolstore.be",
    "license": "LGPL-3",
    "depends": ["website"],
    "assets": {
        "web.assets_frontend": [
            # 1) Lib + boot : scripts classiques, exécutés avant les modules.
            "lolirine_pool_motion/static/src/lib/motion/motion.min.js",
            "lolirine_pool_motion/static/src/js/motion_boot.js",
            # 2) Styles (états initiaux, reduced-motion, polish hover).
            "lolirine_pool_motion/static/src/scss/motion.scss",
            # 3) Helpers + interactions (modules @odoo-module).
            "lolirine_pool_motion/static/src/js/motion_helpers.js",
            "lolirine_pool_motion/static/src/js/reveal.interaction.js",
            "lolirine_pool_motion/static/src/js/stagger.interaction.js",
            "lolirine_pool_motion/static/src/js/count_up.interaction.js",
            "lolirine_pool_motion/static/src/js/press.interaction.js",
        ],
    },
    "installable": True,
    "application": False,
}
