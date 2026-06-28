/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

/*
 * Bouton "retour en haut" :
 *   - apparaît (fondu + léger pop) après ~500px de scroll, disparaît sinon ;
 *   - scroll fluide vers le haut au clic.
 * Le bouton est injecté par views/motion_templates.xml.
 */
export class MotionBackToTop extends Interaction {
    static selector = ".o_motion_top";

    dynamicContent = {
        _root: { "t-on-click": this.scrollTop },
    };

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.visible = false;
        this.ticking = false;
        this.threshold = 500;
        this.onScroll = this.onScroll.bind(this);
    }

    start() {
        // État initial : caché (au cas où le CSS ne l'aurait pas fait).
        this.el.style.opacity = "0";
        this.el.style.pointerEvents = "none";
        window.addEventListener("scroll", this.onScroll, { passive: true });
        this.onScroll();
    }

    _show() {
        this.visible = true;
        this.el.style.pointerEvents = "auto";
        if (!this.motion || this.reduced) {
            this.el.style.opacity = "1";
            return;
        }
        this.motion.animate(
            this.el,
            { opacity: [0, 1], scale: [0.8, 1], y: [10, 0] },
            { duration: 0.3, ease: [0.16, 1, 0.3, 1] }
        );
    }

    _hide() {
        this.visible = false;
        this.el.style.pointerEvents = "none";
        if (!this.motion || this.reduced) {
            this.el.style.opacity = "0";
            return;
        }
        this.motion.animate(
            this.el,
            { opacity: [1, 0], scale: [1, 0.8] },
            { duration: 0.25, ease: [0.4, 0, 1, 1] }
        );
    }

    onScroll() {
        if (this.ticking) {
            return;
        }
        this.ticking = true;
        window.requestAnimationFrame(() => {
            const past = window.scrollY > this.threshold;
            if (past && !this.visible) {
                this._show();
            } else if (!past && this.visible) {
                this._hide();
            }
            this.ticking = false;
        });
    }

    scrollTop() {
        window.scrollTo({
            top: 0,
            behavior: this.reduced ? "auto" : "smooth",
        });
    }

    destroy() {
        window.removeEventListener("scroll", this.onScroll);
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.back_to_top", MotionBackToTop);
