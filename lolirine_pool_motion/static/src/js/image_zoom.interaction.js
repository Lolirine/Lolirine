/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { prefersReducedMotion } from "./motion_helpers";

/*
 * Zoom-loupe AU SURVOL de l'image principale de la fiche produit (global).
 * L'image s'agrandit et suit le curseur, contenue dans son cadre.
 * Coexiste avec le zoom-au-clic natif d'Odoo (clic = lightbox, survol = loupe).
 * Robuste au changement de slide : on relit l'image active à chaque mouvement.
 */
export class MotionImageZoom extends Interaction {
    static selector = "#o-carousel-product";

    dynamicContent = {
        _root: {
            "t-on-mousemove": this.onMove,
            "t-on-mouseleave": this.onLeave,
        },
    };

    setup() {
        this.reduced = prefersReducedMotion();
        this.zoom = 1.9; // facteur d'agrandissement au survol
        this.current = null;
    }

    _activeImg() {
        return (
            this.el.querySelector(".carousel-item.active img") ||
            this.el.querySelector("img")
        );
    }

    _prime(img) {
        if (this.current === img) {
            return;
        }
        this.current = img;
        img.style.transition = "transform 0.18s ease-out";
        img.style.willChange = "transform";
        const wrap = img.closest(".carousel-item") || img.parentElement;
        if (wrap) {
            wrap.style.overflow = "hidden";
        }
    }

    onMove(ev) {
        if (this.reduced) {
            return;
        }
        const img = this._activeImg();
        if (!img) {
            return;
        }
        const r = img.getBoundingClientRect();
        const inside =
            ev.clientX >= r.left &&
            ev.clientX <= r.right &&
            ev.clientY >= r.top &&
            ev.clientY <= r.bottom;

        if (!inside) {
            this._reset(img);
            return;
        }
        this._prime(img);
        const x = ((ev.clientX - r.left) / r.width) * 100;
        const y = ((ev.clientY - r.top) / r.height) * 100;
        img.style.transformOrigin = `${x}% ${y}%`;
        img.style.transform = `scale(${this.zoom})`;
    }

    _reset(img) {
        if (!img) {
            return;
        }
        img.style.transform = "scale(1)";
        img.style.transformOrigin = "center center";
    }

    onLeave() {
        this._reset(this._activeImg());
    }

    destroy() {
        this._reset(this._activeImg());
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.image_zoom", MotionImageZoom);
