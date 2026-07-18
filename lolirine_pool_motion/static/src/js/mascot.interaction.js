/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

/*
 * Mascotte "Bulle" : petite goutte d'eau en bas à gauche dont les yeux
 * suivent le curseur. Cligne des yeux aléatoirement, sursaute au clic.
 * Injectée site-wide, purement décorative (aria-hidden), désactivée sur
 * mobile et en prefers-reduced-motion.
 */
export class MotionMascot extends Interaction {
    static selector = "#wrapwrap";

    dynamicContent = {
        _document: {
            "t-on-mousemove": this.onMove,
            "t-on-click": this.onClick,
        },
    };

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.el_mascot = null;
        this.pupils = [];
        this.blinkTimer = null;
    }

    start() {
        // Pas de mascotte sur petit écran ni en mouvement réduit.
        if (this.reduced || window.innerWidth < 992) {
            return;
        }
        if (document.querySelector(".o_motion_mascot")) {
            return;
        }

        const wrap = document.createElement("div");
        wrap.className = "o_motion_mascot";
        wrap.setAttribute("aria-hidden", "true");
        wrap.innerHTML = `
            <svg viewBox="0 0 100 110" xmlns="http://www.w3.org/2000/svg">
              <path class="o_motion_mascot_body"
                    d="M50 4 C74 38 92 58 92 74 A42 42 0 0 1 8 74 C8 58 26 38 50 4 Z"/>
              <ellipse class="o_motion_mascot_shine" cx="32" cy="60" rx="9" ry="13"/>
              <g class="o_motion_mascot_eyes">
                <circle class="o_motion_mascot_eye" cx="36" cy="72" r="11"/>
                <circle class="o_motion_mascot_eye" cx="64" cy="72" r="11"/>
                <circle class="o_motion_mascot_pupil" cx="36" cy="72" r="5"/>
                <circle class="o_motion_mascot_pupil" cx="64" cy="72" r="5"/>
              </g>
            </svg>`;
        document.body.appendChild(wrap);

        this.el_mascot = wrap;
        this.pupils = Array.from(wrap.querySelectorAll(".o_motion_mascot_pupil"));
        this.eyesGroup = wrap.querySelector(".o_motion_mascot_eyes");

        // Entrée en douceur.
        if (this.motion) {
            this.motion.animate(
                wrap,
                { opacity: [0, 1], y: [24, 0], scale: [0.8, 1] },
                { duration: 0.6, ease: [0.34, 1.56, 0.64, 1], delay: 0.8 }
            );
        } else {
            wrap.style.opacity = "1";
        }

        this._scheduleBlink();
    }

    _scheduleBlink() {
        const delay = 2600 + Math.random() * 4200;
        this.blinkTimer = setTimeout(() => {
            if (this.eyesGroup) {
                this.eyesGroup.classList.add("is-blinking");
                setTimeout(() => {
                    this.eyesGroup?.classList.remove("is-blinking");
                }, 160);
            }
            this._scheduleBlink();
        }, delay);
    }

    onMove(ev) {
        if (!this.el_mascot || !this.pupils.length) {
            return;
        }
        const r = this.el_mascot.getBoundingClientRect();
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height * 0.66;
        const dx = ev.clientX - cx;
        const dy = ev.clientY - cy;
        const dist = Math.hypot(dx, dy) || 1;
        const max = 3.6; // amplitude du regard (unités SVG)
        const ox = (dx / dist) * Math.min(max, dist / 40);
        const oy = (dy / dist) * Math.min(max, dist / 40);
        for (const p of this.pupils) {
            p.style.transform = `translate(${ox}px, ${oy}px)`;
        }
    }

    onClick() {
        if (!this.el_mascot || !this.motion) {
            return;
        }
        this.motion.animate(
            this.el_mascot,
            { scale: [1, 0.86, 1.06, 1] },
            { duration: 0.45, ease: [0.34, 1.56, 0.64, 1] }
        );
    }

    destroy() {
        clearTimeout(this.blinkTimer);
        this.el_mascot?.remove();
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.mascot", MotionMascot);
