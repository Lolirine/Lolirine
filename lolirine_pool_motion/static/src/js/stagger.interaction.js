/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion, MOTION, dataNum } from "./motion_helpers";

/*
 * Apparition en cascade (stagger) des enfants d'un conteneur.
 *
 * Usage :
 *   <div data-motion-stagger>
 *     <div data-motion-item>...</div>
 *     <div data-motion-item>...</div>
 *   </div>
 *
 * Si aucun [data-motion-item] n'est présent, on prend les enfants directs.
 *
 * Options sur le conteneur :
 *   data-motion-gap="0.06"      décalage entre items s
 *   data-motion-distance="20"   amplitude px
 *   data-motion-duration="0.6"  durée s
 *
 * Idéal pour : grille de produits, liste de marques, cartes de bénéfices.
 */
export class MotionStagger extends Interaction {
    static selector = "[data-motion-stagger]";

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.observer = null;
        const explicit = this.el.querySelectorAll(":scope [data-motion-item]");
        this.items = Array.from(explicit.length ? explicit : this.el.children);
    }

    start() {
        if (!this.items.length) {
            return;
        }
        if (!this.motion || this.reduced) {
            this.items.forEach((it) => {
                it.style.opacity = "";
                it.style.transform = "";
                it.classList.add("o_motion_revealed");
            });
            return;
        }

        const gap = dataNum(this.el, "motionGap", MOTION.stagger);
        const distance = dataNum(this.el, "motionDistance", 20);
        const duration = dataNum(this.el, "motionDuration", MOTION.dur);

        this.observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (!entry.isIntersecting) {
                        continue;
                    }
                    this.observer.unobserve(entry.target);
                    this.motion.animate(
                        this.items,
                        { opacity: [0, 1], y: [distance, 0] },
                        {
                            duration,
                            delay: this.motion.stagger(gap),
                            ease: MOTION.easeExpoOut,
                        }
                    ).finished?.then(() => {
                        this.items.forEach((it) => it.classList.add("o_motion_revealed"));
                    });
                }
            },
            { threshold: 0.1, rootMargin: "0px 0px -5% 0px" }
        );
        this.observer.observe(this.el);
    }

    destroy() {
        this.observer?.disconnect();
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.stagger", MotionStagger);
