/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion, MOTION, dataNum } from "./motion_helpers";

/*
 * Reveal au scroll.
 *
 * Usage minimal :
 *   <div data-motion-reveal>...</div>
 *
 * Options (data-attributs) :
 *   data-motion-axis="y|x"      direction (défaut y)
 *   data-motion-dir="up|down|left|right"   sens d'entrée (défaut up / left)
 *   data-motion-distance="32"   amplitude px
 *   data-motion-delay="0.1"     délai s
 *   data-motion-duration="0.7"  durée s
 *   data-motion-once="false"    rejoue à chaque entrée (défaut: une seule fois)
 */
export class MotionReveal extends Interaction {
    static selector = "[data-motion-reveal]";

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.observer = null;
    }

    start() {
        const el = this.el;

        // Pas d'animation possible / souhaitée -> on montre tout de suite.
        if (!this.motion || this.reduced) {
            this._reveal(el, false);
            return;
        }

        const axis = el.dataset.motionAxis === "x" ? "x" : "y";
        const dir = el.dataset.motionDir || (axis === "x" ? "left" : "up");
        const sign = dir === "down" || dir === "right" ? -1 : 1;
        const distance = dataNum(el, "motionDistance", MOTION.distance);
        const delay = dataNum(el, "motionDelay", 0);
        const duration = dataNum(el, "motionDuration", MOTION.dur);
        const once = el.dataset.motionOnce !== "false";

        const animateIn = () => {
            this.motion.animate(
                el,
                { opacity: [0, 1], [axis]: [sign * distance, 0] },
                { duration, delay, ease: MOTION.easeExpoOut }
            ).finished?.then(() => {
                el.style.willChange = "";
                el.classList.add("o_motion_revealed");
            });
        };
        const animateOut = () => {
            el.classList.remove("o_motion_revealed");
            this.motion.animate(
                el,
                { opacity: [1, 0], [axis]: [0, sign * (distance / 2)] },
                { duration: MOTION.durFast, ease: MOTION.easeSoft }
            );
        };

        el.style.willChange = "opacity, transform";
        this.observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        animateIn();
                        if (once) {
                            this.observer.unobserve(entry.target);
                        }
                    } else if (!once) {
                        animateOut();
                    }
                }
            },
            { threshold: 0.15, rootMargin: "0px 0px -8% 0px" }
        );
        this.observer.observe(el);
    }

    _reveal(el) {
        el.style.opacity = "";
        el.style.transform = "";
        el.classList.add("o_motion_revealed");
    }

    destroy() {
        this.observer?.disconnect();
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.reveal", MotionReveal);
