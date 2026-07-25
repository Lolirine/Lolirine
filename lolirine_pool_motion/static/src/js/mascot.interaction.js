/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

const STORAGE_KEY = "lolirine_mascot_off";

/*
 * Mascotte "Bulle" : petite goutte d'eau qui SUIT LE POINTEUR avec un léger
 * retard, en se plaçant à côté du curseur (curseur natif conservé).
 *  - ses yeux regardent le curseur ;
 *  - elle cligne des yeux aléatoirement ;
 *  - après ~2,5 s sans mouvement elle "se gare" : elle devient survolable et
 *    affiche une croix pour être désactivée (choix mémorisé) ;
 *  - desktop uniquement, décorative (aria-hidden), pointer-events neutralisés
 *    tant qu'elle suit la souris.
 */
export class MotionMascot extends Interaction {
    static selector = "#wrapwrap";

    dynamicContent = {
        _document: {
            "t-on-mousemove": this.onMove,
            "t-on-mousedown": this.onDown,
        },
    };

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.el_mascot = null;
        this.pupils = [];
        this.eyesGroup = null;
        this.blinkTimer = null;
        this.idleTimer = null;
        this.raf = null;
        this.tx = window.innerWidth * 0.5;
        this.ty = window.innerHeight * 0.7;
        this.cx = this.tx;
        this.cy = this.ty;
        this.hasMoved = false;
        this.tick = this.tick.bind(this);
        this.onClose = this.onClose.bind(this);
    }

    _isDisabled() {
        try {
            return window.localStorage.getItem(STORAGE_KEY) === "1";
        } catch {
            return false;
        }
    }

    start() {
        // Mascotte réservée au frontend du Pool Store (site 6).
        // #wrapwrap existe sur tous les sites : sans ce filtre, Bulle
        // fuit sur le garde-meuble (site 1) sans son CSS -> goutte noire.
        if (document.documentElement.dataset.websiteId !== "6") {
            return;
        }
        // Jamais dans l'éditeur de site : évite qu'un fragment de mascotte
        // se fige dans l'arch d'une vue lors d'une sauvegarde.
        if (document.querySelector(".o_website_preview") ||
            document.body.classList.contains("editor_enable")) {
            return;
        }
        if (this.reduced || window.innerWidth < 992 || this._isDisabled()) {
            return;
        }
        if (!window.matchMedia("(hover: hover)").matches) {
            return;
        }
        if (document.querySelector(".o_motion_mascot")) {
            return;
        }

        const wrap = document.createElement("div");
        wrap.className = "o_motion_mascot";
        wrap.setAttribute("aria-hidden", "true");
        wrap.innerHTML = `
            <button type="button" class="o_motion_mascot_close"
                    title="Masquer la mascotte" aria-label="Masquer la mascotte">&times;</button>
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
        wrap.querySelector(".o_motion_mascot_close")
            ?.addEventListener("click", this.onClose);

        this._scheduleBlink();
        this.raf = requestAnimationFrame(this.tick);
    }

    /* ---------- suivi du pointeur ---------- */

    onMove(ev) {
        // décalage : la bulle se place en bas à droite du curseur
        this.tx = ev.clientX + 26;
        this.ty = ev.clientY + 26;
        if (!this.hasMoved) {
            this.hasMoved = true;
            this.cx = this.tx;
            this.cy = this.ty;
            this.el_mascot?.classList.add("is-on");
        }
        this.el_mascot?.classList.remove("is-parked");
        clearTimeout(this.idleTimer);
        this.idleTimer = setTimeout(() => {
            this.el_mascot?.classList.add("is-parked");
        }, 2500);
    }

    tick() {
        // interpolation : la bulle rattrape le curseur en douceur
        this.cx += (this.tx - this.cx) * 0.14;
        this.cy += (this.ty - this.cy) * 0.14;
        const wrap = this.el_mascot;
        if (wrap) {
            wrap.style.transform =
                `translate(${this.cx}px, ${this.cy}px) translate(-50%, -50%)`;
            // les yeux regardent le curseur
            const dx = this.tx - 26 - this.cx;
            const dy = this.ty - 26 - this.cy;
            const dist = Math.hypot(dx, dy) || 1;
            const amp = Math.min(3.6, dist / 6);
            const ox = (dx / dist) * amp;
            const oy = (dy / dist) * amp;
            for (const p of this.pupils) {
                p.style.transform = `translate(${ox}px, ${oy}px)`;
            }
        }
        this.raf = requestAnimationFrame(this.tick);
    }

    onDown() {
        if (!this.el_mascot || !this.motion) {
            return;
        }
        const svg = this.el_mascot.querySelector("svg");
        if (svg) {
            this.motion.animate(svg, { scale: [1, 0.82, 1.08, 1] },
                                { duration: 0.4, ease: [0.34, 1.56, 0.64, 1] });
        }
    }

    /* ---------- clignement ---------- */

    _scheduleBlink() {
        const delay = 2600 + Math.random() * 4200;
        this.blinkTimer = setTimeout(() => {
            if (this.eyesGroup) {
                this.eyesGroup.classList.add("is-blinking");
                setTimeout(() => this.eyesGroup?.classList.remove("is-blinking"), 160);
            }
            this._scheduleBlink();
        }, delay);
    }

    /* ---------- désactivation ---------- */

    onClose(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        try {
            window.localStorage.setItem(STORAGE_KEY, "1");
        } catch {
            /* mode privé : la mascotte reviendra au prochain chargement */
        }
        const wrap = this.el_mascot;
        this.el_mascot = null;
        clearTimeout(this.blinkTimer);
        clearTimeout(this.idleTimer);
        cancelAnimationFrame(this.raf);
        if (!wrap) {
            return;
        }
        if (this.motion) {
            this.motion
                .animate(wrap, { opacity: [1, 0], scale: [1, 0.5] },
                         { duration: 0.28, ease: [0.4, 0, 1, 1] })
                .finished?.then(() => wrap.remove());
        } else {
            wrap.remove();
        }
    }

    destroy() {
        clearTimeout(this.blinkTimer);
        clearTimeout(this.idleTimer);
        cancelAnimationFrame(this.raf);
        this.el_mascot?.remove();
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.mascot", MotionMascot);
