/** @odoo-module **/
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class SuggestedMarquee extends Interaction {
    static selector = "html[data-website-id='6'] .o_pool_suggested_wrap";

    setup() {
        this.row = this.el.querySelector(".o_pool_suggested_row");
        if (!this.row) return;

        // 1) on duplique les cartes pour une boucle sans couture
        this.row.innerHTML += this.row.innerHTML;

        this.pos = 0;
        this.speed = 0.4;          // px par frame (~ lent) — ajuste ici
        this.paused = false;
        this._raf = null;
    }

    start() {
        if (!this.row) return;

        // pause au survol
        this.el.addEventListener("mouseenter", () => { this.paused = true; });
        this.el.addEventListener("mouseleave", () => { this.paused = false; });

        const half = this.row.scrollWidth / 2;   // largeur d'un jeu de cartes
        const step = () => {
            if (!this.paused) {
                this.pos += this.speed;
                if (this.pos >= half) this.pos -= half;   // boucle
                this.row.style.transform = `translateX(${-this.pos}px)`;
            }
            this._raf = requestAnimationFrame(step);
        };
        this._raf = requestAnimationFrame(step);
    }

    destroy() {
        if (this._raf) cancelAnimationFrame(this._raf);
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.suggested_marquee", SuggestedMarquee);
