/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion, MOTION } from "./motion_helpers";

/*
 * Retour tactile au clic/appui (press) — fonctionne souris ET tactile.
 * Léger "enfoncement" puis rebond. Utilise les gestes natifs de Motion
 * (press), donc cleanup propre au destroy.
 *
 * S'applique par défaut aux cartes produit du website_sale (.oe_product)
 * et à tout élément marqué [data-motion-press].
 *
 * Le survol (hover) est volontairement laissé au SCSS (plus performant,
 * pas de jank en grille). Voir motion.scss.
 */
export class MotionPress extends Interaction {
    static selector = ".oe_product, [data-motion-press]";

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.cleanups = [];
    }

    start() {
        if (!this.motion || this.reduced || typeof this.motion.press !== "function") {
            return;
        }
        const stop = this.motion.press(this.el, (el) => {
            this.motion.animate(el, { scale: 0.97 }, { duration: 0.12, ease: MOTION.easeSoft });
            // Retour relâché : petit rebond.
            return () =>
                this.motion.animate(el, { scale: 1 }, { duration: 0.4, ease: MOTION.easeBack });
        });
        if (typeof stop === "function") {
            this.cleanups.push(stop);
        }
    }

    destroy() {
        this.cleanups.forEach((fn) => {
            try {
                fn();
            } catch {
                /* no-op */
            }
        });
        this.cleanups = [];
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.press", MotionPress);
