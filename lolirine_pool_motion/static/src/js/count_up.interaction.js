/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion, MOTION, dataNum } from "./motion_helpers";

/*
 * Compteur animé (count-up) quand l'élément entre dans le viewport.
 *
 * Usage :
 *   <span data-motion-count="75">0</span>
 *   <span data-motion-count="98" data-motion-suffix="%">0</span>
 *   <span data-motion-count="44000" data-motion-decimals="0"
 *         data-motion-prefix="" data-motion-suffix=" €">0</span>
 *
 * Options :
 *   data-motion-decimals="0"    nb de décimales
 *   data-motion-duration="1.4"  durée s
 *   data-motion-prefix / data-motion-suffix   texte autour du nombre
 *
 * Idéal pour : "75 boxes", chiffres clés, % de satisfaction, etc.
 */
export class MotionCount extends Interaction {
    static selector = "[data-motion-count]";

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.observer = null;

        this.target = dataNum(this.el, "motionCount", 0);
        this.decimals = dataNum(this.el, "motionDecimals", 0);
        this.duration = dataNum(this.el, "motionDuration", 1.4);
        this.prefix = this.el.dataset.motionPrefix || "";
        this.suffix = this.el.dataset.motionSuffix || "";
        // Format belge francophone : 44 000,00
        this.fmt = new Intl.NumberFormat("fr-BE", {
            minimumFractionDigits: this.decimals,
            maximumFractionDigits: this.decimals,
        });
    }

    _render(value) {
        this.el.textContent = this.prefix + this.fmt.format(value) + this.suffix;
    }

    start() {
        if (!this.motion || this.reduced) {
            this._render(this.target);
            return;
        }
        this._render(0);
        this.observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (!entry.isIntersecting) {
                        continue;
                    }
                    this.observer.unobserve(entry.target);
                    this.motion.animate(0, this.target, {
                        duration: this.duration,
                        ease: MOTION.easeExpoOut,
                        onUpdate: (v) => this._render(v),
                    });
                }
            },
            { threshold: 0.4 }
        );
        this.observer.observe(this.el);
    }

    destroy() {
        this.observer?.disconnect();
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.count", MotionCount);
