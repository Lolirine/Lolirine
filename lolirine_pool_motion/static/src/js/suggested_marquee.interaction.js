/** @odoo-module **/
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class SuggestedMarquee extends Interaction {
    static selector = "html[data-website-id='6'] .o_pool_suggested_wrap";

    setup() {
        this.row = this.el.querySelector(".o_pool_suggested_row");
        if (!this.row) return;
        this.cards = Array.from(this.row.children);
        this.index = 0;
        this.paused = false;
        this.stepCards = 4;          // avance de 4 cartes
        this.interval = 3500;        // pause en ms entre deux sauts
        this._timer = null;
    }

    start() {
        if (!this.row || this.cards.length <= this.stepCards) return;

        this.row.style.transition = "transform 0.6s ease";

        this.el.addEventListener("mouseenter", () => { this.paused = true; });
        this.el.addEventListener("mouseleave", () => { this.paused = false; });

        const tick = () => {
            if (!this.paused) {
                this.index += this.stepCards;
                // si on dépasse, on revient au début
                if (this.index >= this.cards.length) {
                    this.index = 0;
                }
                const target = this.cards[this.index];
                const offset = target.offsetLeft - this.row.offsetLeft;
                this.row.style.transform = `translateX(${-offset}px)`;
            }
        };
        this._timer = setInterval(tick, this.interval);
    }

    destroy() {
        if (this._timer) clearInterval(this._timer);
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.suggested_marquee", SuggestedMarquee);
