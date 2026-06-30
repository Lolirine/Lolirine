/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

/*
 * Mise en valeur de l'icône panier du sidebar.
 *  - Un "clin d'oeil" discret une seule fois au chargement (attire l'oeil).
 *  - Un bounce satisfaisant à chaque ajout (quantité qui augmente), qui
 *    s'enchaîne avec le flyer venant s'y poser.
 * Le relief visuel (taille, pastille, survol, badge) est dans motion.scss.
 */
export class MotionCartIcon extends Interaction {
    static selector = ".o_wsale_my_cart";

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.lastCount = this._count();
        this.observer = null;
    }

    _count() {
        const badge = document.querySelector(".my_cart_quantity");
        return parseInt((badge && badge.textContent) || "0", 10) || 0;
    }

    _icon() {
        return this.el.querySelector("i.fa-shopping-cart") || this.el;
    }

    start() {
        if (!this.motion || this.reduced) {
            return;
        }

        // Clin d'oeil unique au chargement (léger balancement + pop).
        this.waitForTimeout(() => {
            this.motion.animate(
                this._icon(),
                { rotate: [0, -12, 10, -6, 0], scale: [1, 1.18, 1] },
                { duration: 0.7, ease: [0.16, 1, 0.3, 1] }
            );
        }, 900);

        // Bounce à chaque augmentation de quantité.
        const target = this.el.closest("header") || this.el.parentElement || this.el;
        this.observer = new MutationObserver(() => {
            const c = this._count();
            if (c > this.lastCount) {
                this._bounce();
            }
            this.lastCount = c;
        });
        this.observer.observe(target, {
            childList: true,
            characterData: true,
            subtree: true,
        });
    }

    _bounce() {
        this.motion.animate(
            this._icon(),
            { scale: [1, 1.35, 0.92, 1.08, 1] },
            { duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }
        );
    }

    destroy() {
        this.observer?.disconnect();
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.cart_icon", MotionCartIcon);
