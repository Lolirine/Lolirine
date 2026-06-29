/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

/*
 * Mini-cart drawer (vague 2) — LECTURE SEULE.
 *
 * Non-intrusif : ne touche jamais au flux d'ajout d'Odoo.
 *   - S'ouvre quand la quantité du panier augmente (MutationObserver sur
 *     .my_cart_quantity) -> complément naturel du flyer.
 *   - S'ouvre aussi au clic sur l'icône panier (au lieu de naviguer).
 *   - Contenu rendu depuis /lolirine_motion/cart (endpoint JSON lecture seule).
 *   - Édition de quantité : prévue en v2.1.
 */
export class MotionMiniCart extends Interaction {
    static selector = ".o_motion_drawer";

    dynamicContent = {
        ".o_motion_drawer_close": { "t-on-click": this.close },
        ".o_motion_drawer_overlay": { "t-on-click": this.close },
        "_document": { "t-on-keydown": this.onKey },
    };

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.isOpen = false;
        this.busy = false;

        this.overlay = this.el.querySelector(".o_motion_drawer_overlay");
        this.panel = this.el.querySelector(".o_motion_drawer_panel");
        this.body = this.el.querySelector(".o_motion_drawer_body");
        this.totalEl = this.el.querySelector(".o_motion_drawer_total_val");

        // Icônes panier dans l'en-tête (peut y en avoir plusieurs).
        this.cartLinks = Array.from(
            document.querySelectorAll('a[href$="/shop/cart"]')
        );
        this.lastCount = this._badgeCount();

        this.onCartClick = this.onCartClick.bind(this);
        this.observer = null;
    }

    start() {
        // Clic sur l'icône panier -> ouvre le drawer plutôt que naviguer.
        this.cartLinks.forEach((a) =>
            a.addEventListener("click", this.onCartClick)
        );

        // Détecte une augmentation de quantité (ajout au panier).
        const target =
            this.cartLinks[0]?.closest("header") ||
            this.cartLinks[0]?.parentElement ||
            document.querySelector("header#top");
        if (target) {
            this.observer = new MutationObserver(() => {
                const c = this._badgeCount();
                if (c > this.lastCount && !this.isOpen) {
                    this.open();
                }
                this.lastCount = c;
            });
            this.observer.observe(target, {
                childList: true,
                characterData: true,
                subtree: true,
            });
        }
    }

    _badgeCount() {
        const badge = document.querySelector(".my_cart_quantity");
        return parseInt((badge && badge.textContent) || "0", 10) || 0;
    }

    onCartClick(ev) {
        // On garde le clic-droit / nouvel onglet natif.
        if (ev.metaKey || ev.ctrlKey || ev.button === 1) {
            return;
        }
        ev.preventDefault();
        this.open();
    }

    onKey(ev) {
        if (ev.key === "Escape" && this.isOpen) {
            this.close();
        }
    }

    async open() {
        if (this.isOpen) {
            this._load();
            return;
        }
        this.isOpen = true;
        this.el.classList.add("is-open");
        this.el.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";

        if (!this.motion || this.reduced) {
            this.overlay.style.opacity = "1";
            this.panel.style.transform = "translateX(0)";
        } else {
            this.motion.animate(this.overlay, { opacity: [0, 1] }, { duration: 0.25 });
            this.motion.animate(
                this.panel,
                { x: ["100%", "0%"] },
                { duration: 0.4, ease: [0.16, 1, 0.3, 1] }
            );
        }
        this._load();
    }

    close() {
        if (!this.isOpen) {
            return;
        }
        this.isOpen = false;
        this.el.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";

        const finish = () => {
            this.el.classList.remove("is-open");
        };
        if (!this.motion || this.reduced) {
            this.overlay.style.opacity = "0";
            this.panel.style.transform = "translateX(100%)";
            finish();
            return;
        }
        this.motion.animate(this.overlay, { opacity: [1, 0] }, { duration: 0.2 });
        this.motion
            .animate(
                this.panel,
                { x: ["0%", "100%"] },
                { duration: 0.3, ease: [0.4, 0, 1, 1] }
            )
            .finished?.then(finish);
    }

    async _load() {
        if (this.busy) {
            return;
        }
        this.busy = true;
        try {
            const res = await fetch("/lolirine_motion/cart", {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await res.json();
            this._render(data);
        } catch {
            this.body.innerHTML = "";
            const err = document.createElement("div");
            err.className = "o_motion_drawer_empty";
            err.textContent = "Impossible de charger le panier.";
            this.body.appendChild(err);
        } finally {
            this.busy = false;
        }
    }

    _money(amount, currency) {
        try {
            return new Intl.NumberFormat("fr-BE", {
                style: "currency",
                currency: currency || "EUR",
            }).format(amount || 0);
        } catch {
            return `${(amount || 0).toFixed(2)} ${currency || "EUR"}`;
        }
    }

    _render(data) {
        const cur = data.currency || "EUR";
        this.body.innerHTML = "";

        if (!data.lines || !data.lines.length) {
            const empty = document.createElement("div");
            empty.className = "o_motion_drawer_empty";
            empty.textContent = "Votre panier est vide.";
            this.body.appendChild(empty);
            this.totalEl.textContent = this._money(0, cur);
            return;
        }

        for (const line of data.lines) {
            const row = document.createElement("a");
            row.className = "o_motion_drawer_line";
            row.href = line.url || "/shop";

            const img = document.createElement("img");
            img.className = "o_motion_drawer_thumb";
            img.src = line.image_url;
            img.alt = "";
            img.loading = "lazy";

            const info = document.createElement("div");
            info.className = "o_motion_drawer_info";

            const name = document.createElement("div");
            name.className = "o_motion_drawer_name";
            name.textContent = line.name;

            const meta = document.createElement("div");
            meta.className = "o_motion_drawer_meta";
            const q = Number(line.qty || 0);
            const qty = Number.isInteger(q) ? q : q.toFixed(2);
            meta.textContent = `${qty} × ${this._money(
                (line.price_total || 0) / (q || 1),
                cur
            )}`;

            info.appendChild(name);
            info.appendChild(meta);

            const price = document.createElement("div");
            price.className = "o_motion_drawer_price";
            price.textContent = this._money(line.price_total, cur);

            row.appendChild(img);
            row.appendChild(info);
            row.appendChild(price);
            this.body.appendChild(row);
        }

        this.totalEl.textContent = this._money(data.amount_total, cur);

        // Petite cascade d'apparition des lignes.
        if (this.motion && !this.reduced) {
            const rows = this.body.querySelectorAll(".o_motion_drawer_line");
            this.motion.animate(
                rows,
                { opacity: [0, 1], x: [16, 0] },
                { duration: 0.35, delay: this.motion.stagger(0.05), ease: [0.16, 1, 0.3, 1] }
            );
        }
    }

    destroy() {
        this.observer?.disconnect();
        this.cartLinks.forEach((a) =>
            a.removeEventListener("click", this.onCartClick)
        );
        document.body.style.overflow = "";
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.mini_cart", MotionMiniCart);
