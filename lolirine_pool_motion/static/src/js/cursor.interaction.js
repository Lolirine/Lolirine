/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { prefersReducedMotion } from "./motion_helpers";

/*
 * Curseur suiveur : un anneau qui suit la souris avec un léger retard, et
 * qui grossit au survol des éléments cliquables. Le curseur natif reste
 * visible (choix volontaire sur une boutique : lisibilité des liens/prix).
 * Desktop uniquement, purement décoratif, pointer-events: none.
 */
export class MotionCursor extends Interaction {
    static selector = "#wrapwrap";

    dynamicContent = {
        _document: {
            "t-on-mousemove": this.onMove,
            "t-on-mousedown": this.onDown,
            "t-on-mouseup": this.onUp,
            "t-on-mouseover": this.onOver,
        },
    };

    setup() {
        this.reduced = prefersReducedMotion();
        this.ring = null;
        this.x = 0;
        this.y = 0;
        this.rx = 0;
        this.ry = 0;
        this.raf = null;
        this.tick = this.tick.bind(this);
    }

    start() {
        if (this.reduced || window.innerWidth < 992 || !window.matchMedia("(hover: hover)").matches) {
            return;
        }
        if (document.querySelector(".o_motion_cursor")) {
            return;
        }
        const ring = document.createElement("div");
        ring.className = "o_motion_cursor";
        ring.setAttribute("aria-hidden", "true");
        document.body.appendChild(ring);
        this.ring = ring;
        this.raf = requestAnimationFrame(this.tick);
    }

    onMove(ev) {
        this.x = ev.clientX;
        this.y = ev.clientY;
        if (this.ring && !this.ring.classList.contains("is-on")) {
            this.ring.classList.add("is-on");
        }
    }

    onOver(ev) {
        if (!this.ring) {
            return;
        }
        const clickable = ev.target.closest(
            "a, button, input[type=submit], .btn, .oe_product, [role=button]"
        );
        this.ring.classList.toggle("is-hover", !!clickable);
    }

    onDown() {
        this.ring?.classList.add("is-down");
    }

    onUp() {
        this.ring?.classList.remove("is-down");
    }

    tick() {
        // interpolation : le halo suit avec un léger retard
        this.rx += (this.x - this.rx) * 0.18;
        this.ry += (this.y - this.ry) * 0.18;
        if (this.ring) {
            this.ring.style.transform =
                `translate(${this.rx}px, ${this.ry}px) translate(-50%, -50%)`;
        }
        this.raf = requestAnimationFrame(this.tick);
    }

    destroy() {
        cancelAnimationFrame(this.raf);
        this.ring?.remove();
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.cursor", MotionCursor);
