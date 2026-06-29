/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

/*
 * Header rétractable : se cache en descendant, réapparaît en remontant.
 * Conçu pour une barre HORIZONTALE en haut uniquement.
 *
 * Garde-fous (no-op si une condition n'est pas réunie) :
 *   - bail si reduced-motion ou lib absente.
 *   - opt-out explicite : <header data-motion-header="off">.
 *   - bail si l'effet natif Odoo "Disappears"/"Fade out" est actif (doublon).
 *   - bail si le header n'est pas fixe/sticky (sinon ça n'a pas de sens).
 *   - bail si le layout est une SIDEBAR verticale (large<haut) : on ne fait
 *     jamais glisser une colonne de navigation hors de l'écran. Détection
 *     géométrique (indépendante du thème) + marqueurs de classe Odoo.
 *
 * Conseil (barre horizontale) : régler l'effet de défilement du header sur
 * "Fixe" dans l'éditeur, puis cette interaction ajoute le masquage fluide.
 */
export class MotionHeaderScroll extends Interaction {
    static selector = "header#top";

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.lastY = window.scrollY;
        this.hidden = false;
        this.ticking = false;
        this.onScroll = this.onScroll.bind(this);
    }

    _isSidebar() {
        // Marqueurs de thème connus pour un header vertical / latéral.
        const cls = this.el.className || "";
        if (/o_header_sidebar|o_header_vertical|o_sidebar/.test(cls)) {
            return true;
        }
        if (document.body.classList.contains("o_header_sidebar")) {
            return true;
        }
        // Détection géométrique : une vraie barre horizontale est LARGE et BASSE.
        const r = this.el.getBoundingClientRect();
        const isTopBar = r.width >= window.innerWidth * 0.6 && r.height <= window.innerHeight * 0.5;
        return !isTopBar;
    }

    _eligible() {
        if (!this.motion || this.reduced) {
            return false;
        }
        if (this.el.dataset.motionHeader === "off") {
            return false;
        }
        if (
            this.el.classList.contains("o_header_disappears") ||
            this.el.classList.contains("o_header_fade_out")
        ) {
            return false;
        }
        if (this._isSidebar()) {
            return false; // sidebar : on laisse la navigation en place.
        }
        const pos = getComputedStyle(this.el).position;
        return pos === "fixed" || pos === "sticky";
    }

    start() {
        if (!this._eligible()) {
            return;
        }
        this.headerH = this.el.offsetHeight || 80;
        window.addEventListener("scroll", this.onScroll, { passive: true });
    }

    onScroll() {
        if (this.ticking) {
            return;
        }
        this.ticking = true;
        window.requestAnimationFrame(() => {
            const y = window.scrollY;
            const goingDown = y > this.lastY;
            const pastHeader = y > this.headerH + 40;

            if (goingDown && pastHeader && !this.hidden) {
                this.hidden = true;
                this.motion.animate(
                    this.el,
                    { y: -(this.headerH + 8) },
                    { duration: 0.35, ease: [0.4, 0, 1, 1] }
                );
            } else if ((!goingDown || y <= this.headerH) && this.hidden) {
                this.hidden = false;
                this.motion.animate(
                    this.el,
                    { y: 0 },
                    { duration: 0.45, ease: [0.16, 1, 0.3, 1] }
                );
            }
            this.lastY = y;
            this.ticking = false;
        });
    }

    destroy() {
        window.removeEventListener("scroll", this.onScroll);
    }
}

registry
    .category("public.interactions")
    .add("lolirine_pool_motion.header_scroll", MotionHeaderScroll);
