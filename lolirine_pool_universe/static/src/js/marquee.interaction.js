/** @odoo-module **/
/**
 * Défilés produits : navigation manuelle + défilement automatique.
 *
 * - Flèches ‹ › (ordinateur), glisser à la souris, balayage au doigt, pavé tactile.
 * - Sans action du visiteur, le défilé avance tout seul ; il reprend
 *   RESUME_DELAY ms après la dernière action (ou quand la souris quitte le défilé).
 * - Boucle infinie : les deux groupes de cartes sont identiques, on « recolle »
 *   la position d'une largeur de groupe sans que ça se voie.
 * - Sans JavaScript (aperçu du constructeur, éditeur) : l'animation CSS d'origine reste.
 * - « Réduire les animations » activé : pas d'automatique, défilement manuel natif (CSS).
 */
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const RESUME_DELAY = 2500;
const DRAG_THRESHOLD = 6;

export class PoolUniverseMarquee extends Interaction {
    static selector = ".s_pu_viewport";

    start() {
        if (document.body.classList.contains("editor_enable")) {
            return;
        }
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }
        const track = this.el.querySelector(":scope > .s_pu_track");
        const groups = track ? track.querySelectorAll(":scope > .s_pu_group") : [];
        if (groups.length < 2) {
            return;
        }
        this.groups = groups;

        // Trop peu de produits pour remplir l'écran : on garde l'animation CSS
        if (groups[1].offsetLeft - groups[0].offsetLeft <= this.el.clientWidth) {
            return;
        }

        // Zone qui défile (le conteneur d'origine garde les flèches, fixes)
        const scroller = document.createElement("div");
        scroller.className = "s_pu_scroll";
        this.el.insertBefore(scroller, track);
        scroller.appendChild(track);
        this.scroller = scroller;

        const prev = this.makeButton("prev", "Produits précédents", "fa-chevron-left");
        const next = this.makeButton("next", "Produits suivants", "fa-chevron-right");
        this.el.append(prev, next);
        this.el.classList.add("s_pu_js");

        this.registerCleanup(() => {
            cancelAnimationFrame(this.frame);
            clearTimeout(this.resumeTimer);
            clearTimeout(this.smoothTimer);
            this.observer?.disconnect();
            prev.remove();
            next.remove();
            this.el.insertBefore(track, scroller);
            scroller.remove();
            this.el.classList.remove("s_pu_js");
        });

        this.dir = this.el.closest(".s_pu_reverse") ? -1 : 1;
        const duration = parseFloat(getComputedStyle(this.el).getPropertyValue("--pu-duration")) || 80;
        this.speed = this.groupWidth() / duration; // px par seconde
        this.pos = this.dir < 0 ? this.groupWidth() : 0;
        this.setScroll(this.pos);

        this.hovered = false;
        this.focused = false;
        this.userActive = false;
        this.visible = true;
        this.dragging = false;

        // Événements
        this.addListener(prev, "click", () => this.step(-1));
        this.addListener(next, "click", () => this.step(1));
        this.addListener(scroller, "scroll", () => this.onScroll(), { passive: true });
        this.addListener(scroller, "wheel", (ev) => {
            // Seulement un défilement horizontal (pavé tactile, Maj + molette)
            if (Math.abs(ev.deltaX) > Math.abs(ev.deltaY)) {
                this.markActive();
            }
        }, { passive: true });
        this.addListener(scroller, "touchstart", () => this.markActive(), { passive: true });
        this.addListener(this.el, "mouseenter", () => { this.hovered = true; });
        this.addListener(this.el, "mouseleave", () => { this.hovered = false; this.markActive(); });
        this.addListener(this.el, "focusin", () => { this.focused = true; });
        this.addListener(this.el, "focusout", () => { this.focused = false; this.markActive(); });
        this.addListener(scroller, "pointerdown", (ev) => this.onPointerDown(ev));
        this.addListener(window, "pointermove", (ev) => this.onPointerMove(ev));
        this.addListener(window, "pointerup", () => this.onPointerUp());
        this.addListener(window, "pointercancel", () => this.onPointerUp());
        this.addListener(scroller, "dragstart", (ev) => ev.preventDefault());
        // Après un glisser, le clic ne doit pas ouvrir la fiche produit
        this.addListener(scroller, "click", (ev) => {
            if (this.blockClick) {
                ev.preventDefault();
                ev.stopPropagation();
                this.blockClick = false;
            }
        }, { capture: true });
        this.addListener(window, "resize", () => {
            this.pos = this.wrap(this.scroller.scrollLeft);
        });

        // N'anime que les défilés visibles à l'écran
        if ("IntersectionObserver" in window) {
            this.observer = new IntersectionObserver((entries) => {
                this.visible = entries.some((entry) => entry.isIntersecting);
            });
            this.observer.observe(this.el);
        }

        this.last = performance.now();
        this.frame = requestAnimationFrame((t) => this.tick(t));
    }

    makeButton(kind, label, icon) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `s_pu_nav s_pu_nav_${kind}`;
        button.setAttribute("aria-label", label);
        button.title = label;
        button.innerHTML = `<i class="fa ${icon}" aria-hidden="true"></i>`;
        return button;
    }

    groupWidth() {
        return this.groups[1].offsetLeft - this.groups[0].offsetLeft;
    }

    wrap(x) {
        const width = this.groupWidth();
        if (width <= 0) {
            return x;
        }
        return ((x % width) + width) % width;
    }

    setScroll(x) {
        this.scroller.scrollLeft = x;
        this.lastSet = this.scroller.scrollLeft;
    }

    get paused() {
        return this.hovered || this.focused || this.userActive || this.dragging
            || !this.visible || document.hidden;
    }

    tick(now) {
        const dt = Math.min(0.1, (now - this.last) / 1000);
        this.last = now;
        if (!this.paused) {
            this.pos = this.wrap(this.pos + this.dir * this.speed * dt);
            this.setScroll(this.pos);
        }
        this.frame = requestAnimationFrame((t) => this.tick(t));
    }

    /** Une action du visiteur : pause, puis reprise après RESUME_DELAY. */
    markActive() {
        this.userActive = true;
        clearTimeout(this.resumeTimer);
        this.resumeTimer = setTimeout(() => {
            this.userActive = false;
            this.pos = this.wrap(this.scroller.scrollLeft);
            this.last = performance.now();
        }, RESUME_DELAY);
    }

    onScroll() {
        const current = this.scroller.scrollLeft;
        if (Math.abs(current - this.lastSet) < 1.5) {
            return; // c'est nous qui avons bougé
        }
        this.markActive();
        // Boucle infinie pendant la navigation manuelle
        const width = this.groupWidth();
        const max = this.scroller.scrollWidth - this.scroller.clientWidth;
        if (!this.dragging && !this.smooth) {
            if (current <= 1) {
                this.setScroll(current + width);
            } else if (current >= max - 1) {
                this.setScroll(current - width);
            }
        }
        this.pos = this.wrap(this.scroller.scrollLeft);
        this.lastSet = this.scroller.scrollLeft;
    }

    /** Flèches : avance d'environ 80 % de la largeur visible, en douceur. */
    step(direction) {
        this.markActive();
        const width = this.groupWidth();
        const card = this.scroller.querySelector(".s_pu_item");
        const unit = card ? card.getBoundingClientRect().width + 16 : 220;
        const distance = Math.max(unit, Math.floor((this.scroller.clientWidth * 0.8) / unit) * unit);
        const max = this.scroller.scrollWidth - this.scroller.clientWidth;
        let start = this.scroller.scrollLeft;
        // Se replacer dans la copie qui laisse la place d'avancer (invisible)
        if (direction < 0 && start - distance < 0) {
            start += width;
        } else if (direction > 0 && start + distance > max) {
            start -= width;
        }
        this.setScroll(start);
        this.smooth = true;
        clearTimeout(this.smoothTimer);
        this.smoothTimer = setTimeout(() => { this.smooth = false; }, 700);
        this.scroller.scrollTo({ left: start + direction * distance, behavior: "smooth" });
    }

    // Glisser à la souris (le tactile utilise le défilement natif)
    onPointerDown(ev) {
        if (ev.pointerType !== "mouse" || ev.button !== 0) {
            return;
        }
        this.drag = { x: ev.clientX, scroll: this.scroller.scrollLeft, moved: false };
    }

    onPointerMove(ev) {
        if (!this.drag) {
            return;
        }
        const dx = ev.clientX - this.drag.x;
        if (!this.drag.moved && Math.abs(dx) < DRAG_THRESHOLD) {
            return;
        }
        if (!this.drag.moved) {
            this.drag.moved = true;
            this.dragging = true;
            this.scroller.classList.add("s_pu_dragging");
        }
        this.markActive();
        const target = this.wrap(this.drag.scroll - dx);
        this.setScroll(target);
        this.pos = target;
    }

    onPointerUp() {
        if (!this.drag) {
            return;
        }
        if (this.drag.moved) {
            this.blockClick = true;
            this.waitForTimeout(() => { this.blockClick = false; }, 300);
            this.scroller.classList.remove("s_pu_dragging");
            this.markActive();
        }
        this.dragging = false;
        this.drag = null;
    }
}

registry
    .category("public.interactions")
    .add("lolirine_pool_universe.marquee", PoolUniverseMarquee);
