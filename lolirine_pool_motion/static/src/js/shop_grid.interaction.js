/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion, MOTION, dataNum } from "./motion_helpers";

/*
 * Cascade automatique de la grille boutique (/shop) — aucune édition de template.
 * S'accroche à #products_grid et anime ses cartes .oe_product en cascade au chargement.
 *
 * Si le thème a renommé le conteneur, poser manuellement data-motion-stagger
 * sur la grille : l'interaction générique "stagger" prend alors le relais.
 */
export class MotionShopGrid extends Interaction {
    static selector = "#products_grid";

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        // Si déjà géré par l'interaction générique, on ne double pas.
        this.skip = this.el.hasAttribute("data-motion-stagger");
        this.items = Array.from(this.el.querySelectorAll(".oe_product"));
    }

    start() {
        if (this.skip || !this.items.length) {
            return;
        }
        if (!this.motion || this.reduced) {
            this.items.forEach((it) => it.classList.add("o_motion_revealed"));
            return;
        }
        const gap = dataNum(this.el, "motionGap", 0.05);
        const duration = dataNum(this.el, "motionDuration", 0.55);
        this.motion
            .animate(
                this.items,
                { opacity: [0, 1], y: [18, 0] },
                { duration, delay: this.motion.stagger(gap), ease: MOTION.easeExpoOut }
            )
            .finished?.then(() => {
                this.items.forEach((it) => it.classList.add("o_motion_revealed"));
            });
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.shop_grid", MotionShopGrid);
