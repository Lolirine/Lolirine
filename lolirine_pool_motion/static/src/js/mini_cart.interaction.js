/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

/*
 * Mini-cart drawer (vagues 2 / 2.1).
 *
 *  - S'ouvre quand la quantité du panier augmente (MutationObserver sur
 *    .my_cart_quantity) et au clic sur l'icône panier.
 *  - Contenu lu depuis /lolirine_motion/cart (endpoint JSON lecture seule).
 *  - v2.1 : édition de quantité (− / +) et suppression de ligne via la route
 *    officielle /shop/cart/update_json, puis rafraîchissement du drawer.
 *    On ne réécrit jamais la logique panier d'Odoo : on l'appelle.
 */
export class MotionMiniCart extends Interaction {
    static selector = ".o_motion_drawer";

    dynamicContent = {
        ".o_motion_drawer_close": { "t-on-click": this.close },
        ".o_motion_drawer_overlay": { "t-on-click": this.close },
        ".o_motion_drawer_body": { "t-on-click": this.onBodyClick },
        "_document": { "t-on-keydown": this.onKey },
    };

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.isOpen = false;
        this.busy = false;
        this.updating = false;

        this.overlay = this.el.querySelector(".o_motion_drawer_overlay");
        this.panel = this.el.querySelector(".o_motion_drawer_panel");
        this.body = this.el.querySelector(".o_motion_drawer_body");
        this.totalEl = this.el.querySelector(".o_motion_drawer_total_val");

        this.cartLinks = Array.from(
            document.querySelectorAll('a[href$="/shop/cart"]')
        );
        this.lastCount = this._badgeCount();

        this.onCartClick = this.onCartClick.bind(this);
        this.observer = null;
    }

    start() {
        this.cartLinks.forEach((a) =>
            a.addEventListener("click", this.onCartClick)
        );

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

    /* ---------- helpers ---------- */

    _badgeCount() {
        const badge = document.querySelector(".my_cart_quantity");
        return parseInt((badge && badge.textContent) || "0", 10) || 0;
    }

    _updateBadge(count) {
        const badge = document.querySelector(".my_cart_quantity");
        if (badge) {
            badge.textContent = count;
            if (this.motion && !this.reduced) {
                this.motion.animate(
                    badge,
                    { scale: [1, 1.4, 1] },
                    { duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }
                );
            }
        }
        this.lastCount = count;
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

    async _fetchCart() {
        const res = await fetch("/lolirine_motion/cart", {
            headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        return res.json();
    }

    async _rpc(route, params = {}) {
        const res = await fetch(route, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params }),
        });
        const data = await res.json();
        if (data.error) {
            throw new Error(
                data.error.data?.message || data.error.message || "RPC error"
            );
        }
        return data.result;
    }

    /* ---------- open / close ---------- */

    onCartClick(ev) {
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
            this._load(false);
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
        this._load(true);
    }

    close() {
        if (!this.isOpen) {
            return;
        }
        this.isOpen = false;
        this.el.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";

        const finish = () => this.el.classList.remove("is-open");
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

    /* ---------- data + render ---------- */

    async _load(animate) {
        if (this.busy) {
            return;
        }
        this.busy = true;
        try {
            const data = await this._fetchCart();
            if (data && data.error) {
                this.body.innerHTML = "";
                const err = document.createElement("div");
                err.className = "o_motion_drawer_empty";
                err.textContent = "Panier indisponible : " + data.error;
                this.body.appendChild(err);
                return;
            }
            this._render(data, animate);
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

    _qbtn(act, icon, label) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "o_motion_drawer_qbtn";
        b.dataset.act = act;
        b.setAttribute("aria-label", label);
        const i = document.createElement("i");
        i.className = `fa ${icon}`;
        i.setAttribute("aria-hidden", "true");
        b.appendChild(i);
        return b;
    }

    _render(data, animate) {
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
            const q = Number(line.qty || 0);
            const unit = (line.price_total || 0) / (q || 1);

            const row = document.createElement("div");
            row.className = "o_motion_drawer_line";
            row.dataset.lineId = line.id;
            row.dataset.productId = line.product_id;
            row.dataset.qty = q;

            // Zone cliquable -> fiche produit.
            const link = document.createElement("a");
            link.className = "o_motion_drawer_link";
            link.href = line.url || "/shop";

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
            meta.textContent = `${this._money(unit, cur)} / unité`;

            info.appendChild(name);
            info.appendChild(meta);
            link.appendChild(img);
            link.appendChild(info);

            // Contrôles quantité.
            const controls = document.createElement("div");
            controls.className = "o_motion_drawer_controls";
            const dec = this._qbtn("dec", "fa-minus", "Diminuer la quantité");
            const val = document.createElement("span");
            val.className = "o_motion_drawer_qval";
            val.textContent = Number.isInteger(q) ? q : q.toFixed(2);
            const inc = this._qbtn("inc", "fa-plus", "Augmenter la quantité");
            controls.appendChild(dec);
            controls.appendChild(val);
            controls.appendChild(inc);

            // Colonne droite : prix + suppression.
            const right = document.createElement("div");
            right.className = "o_motion_drawer_right";
            const price = document.createElement("div");
            price.className = "o_motion_drawer_price";
            price.textContent = this._money(line.price_total, cur);
            const rm = this._qbtn("remove", "fa-trash-o", "Retirer l'article");
            rm.classList.add("o_motion_drawer_remove");
            right.appendChild(price);
            right.appendChild(rm);

            row.appendChild(link);
            row.appendChild(controls);
            row.appendChild(right);
            this.body.appendChild(row);
        }

        this.totalEl.textContent = this._money(data.amount_total, cur);

        if (animate && this.motion && !this.reduced) {
            const rows = this.body.querySelectorAll(".o_motion_drawer_line");
            this.motion.animate(
                rows,
                { opacity: [0, 1], x: [16, 0] },
                { duration: 0.35, delay: this.motion.stagger(0.05), ease: [0.16, 1, 0.3, 1] }
            );
        }
    }

    /* ---------- édition (v2.1) ---------- */

    onBodyClick(ev) {
        const btn = ev.target.closest("[data-act]");
        if (!btn) {
            return; // clic sur le lien produit : navigation normale.
        }
        ev.preventDefault();
        const row = btn.closest("[data-line-id]");
        if (!row) {
            return;
        }
        const lineId = parseInt(row.dataset.lineId, 10);
        const productId = parseInt(row.dataset.productId, 10);
        const curQty = parseFloat(row.dataset.qty) || 0;
        const act = btn.dataset.act;

        let newQty = curQty;
        if (act === "inc") {
            newQty = curQty + 1;
        } else if (act === "dec") {
            newQty = curQty - 1;
        } else if (act === "remove") {
            newQty = 0;
        }
        if (newQty < 0) {
            newQty = 0;
        }
        this._setQty(lineId, productId, newQty, row);
    }

    async _setQty(lineId, productId, qty, row) {
        if (this.updating) {
            return;
        }
        this.updating = true;
        row?.classList.add("is-updating");
        try {
            await this._rpc("/shop/cart/update_json", {
                line_id: lineId,
                product_id: productId,
                set_qty: qty,
            });
            const data = await this._fetchCart();
            this._render(data, false);
            this._updateBadge(data.count);
        } catch {
            row?.classList.remove("is-updating");
        } finally {
            this.updating = false;
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
