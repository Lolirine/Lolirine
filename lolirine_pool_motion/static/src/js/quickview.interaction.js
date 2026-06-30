/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

/*
 * Quickview produit (vague 2, option simple).
 *
 *  - Pose une loupe sur chaque carte de la grille boutique (.oe_product).
 *  - Au clic : overlay centré, contenu rendu depuis /lolirine_motion/product/<id>.
 *  - Produit simple : bouton "Ajouter au panier" (via /shop/cart/update_json) ;
 *    l'ajout met à jour le badge -> déclenche rebond + ouverture du drawer.
 *  - Produit à variantes : bouton "Voir le produit" (fiche complète).
 *  - 100 % lecture seule côté affichage ; l'ajout passe par la route officielle.
 */
export class MotionQuickview extends Interaction {
    static selector = ".o_motion_qv";

    dynamicContent = {
        ".o_motion_qv_close": { "t-on-click": this.close },
        ".o_motion_qv_overlay": { "t-on-click": this.close },
        ".o_motion_qv_content": { "t-on-click": this.onContentClick },
        "_document": { "t-on-keydown": this.onKey },
    };

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
        this.isOpen = false;
        this.busy = false;
        this.adding = false;

        this.overlay = this.el.querySelector(".o_motion_qv_overlay");
        this.dialog = this.el.querySelector(".o_motion_qv_dialog");
        this.content = this.el.querySelector(".o_motion_qv_content");

        this.cards = [];
        this.onCardBtn = this.onCardBtn.bind(this);
    }

    start() {
        // Injecte une loupe sur chaque carte produit (sans décaler la mise en page).
        this.cards = Array.from(document.querySelectorAll(".oe_product"));
        for (const card of this.cards) {
            if (card.querySelector(".o_motion_qv_btn")) {
                continue;
            }
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "o_motion_qv_btn";
            btn.setAttribute("aria-label", "Aperçu rapide");
            const i = document.createElement("i");
            i.className = "fa fa-search-plus";
            i.setAttribute("aria-hidden", "true");
            btn.appendChild(i);
            btn.addEventListener("click", this.onCardBtn);
            card.appendChild(btn);
        }
    }

    _templateId(card) {
        const input = card.querySelector('input[name="product_template_id"]');
        if (input && input.value) {
            return parseInt(input.value, 10);
        }
        const link = card.querySelector('a[href*="/shop/"]');
        if (link) {
            const m = link.getAttribute("href").match(/-(\d+)(?:[/?#]|$)/);
            if (m) {
                return parseInt(m[1], 10);
            }
        }
        const ds = card.dataset.productTemplateId || card.dataset.oeId;
        return ds ? parseInt(ds, 10) : null;
    }

    onCardBtn(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const card = ev.currentTarget.closest(".oe_product");
        const id = card && this._templateId(card);
        if (id) {
            this.openFor(id);
        }
    }

    onKey(ev) {
        if (ev.key === "Escape" && this.isOpen) {
            this.close();
        }
    }

    /* ---------- open / close ---------- */

    openFor(tmplId) {
        if (!this.isOpen) {
            this.isOpen = true;
            this.el.classList.add("is-open");
            this.el.setAttribute("aria-hidden", "false");
            document.body.style.overflow = "hidden";
            if (!this.motion || this.reduced) {
                this.overlay.style.opacity = "1";
                this.dialog.style.opacity = "1";
                this.dialog.style.transform = "none";
            } else {
                this.motion.animate(this.overlay, { opacity: [0, 1] }, { duration: 0.22 });
                this.motion.animate(
                    this.dialog,
                    { opacity: [0, 1], scale: [0.92, 1], y: [12, 0] },
                    { duration: 0.35, ease: [0.16, 1, 0.3, 1] }
                );
            }
        }
        this._load(tmplId);
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
            this.content.innerHTML =
                '<div class="o_motion_qv_loading">Chargement…</div>';
        };
        if (!this.motion || this.reduced) {
            this.overlay.style.opacity = "0";
            this.dialog.style.opacity = "0";
            finish();
            return;
        }
        this.motion.animate(this.overlay, { opacity: [1, 0] }, { duration: 0.2 });
        this.motion
            .animate(
                this.dialog,
                { opacity: [1, 0], scale: [1, 0.95] },
                { duration: 0.22, ease: [0.4, 0, 1, 1] }
            )
            .finished?.then(finish);
    }

    /* ---------- data + render ---------- */

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

    async _load(tmplId) {
        if (this.busy) {
            return;
        }
        this.busy = true;
        this.content.innerHTML =
            '<div class="o_motion_qv_loading">Chargement…</div>';
        try {
            const res = await fetch(`/lolirine_motion/product/${tmplId}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await res.json();
            if (!data || data.error) {
                throw new Error(data && data.error);
            }
            this._render(data);
        } catch {
            this.content.innerHTML =
                '<div class="o_motion_qv_loading">Aperçu indisponible.</div>';
        } finally {
            this.busy = false;
        }
    }

    _render(data) {
        const cur = data.currency || "EUR";
        this.content.innerHTML = "";

        const media = document.createElement("div");
        media.className = "o_motion_qv_media";
        const img = document.createElement("img");
        img.src = data.image_url;
        img.alt = data.name;
        img.loading = "lazy";
        media.appendChild(img);

        const info = document.createElement("div");
        info.className = "o_motion_qv_info";

        const title = document.createElement("h3");
        title.className = "o_motion_qv_title";
        title.textContent = data.name;
        info.appendChild(title);

        const priceWrap = document.createElement("div");
        priceWrap.className = "o_motion_qv_price";
        if (data.has_discount) {
            const old = document.createElement("span");
            old.className = "o_motion_qv_oldprice";
            old.textContent = this._money(data.list_price, cur);
            priceWrap.appendChild(old);
        }
        const now = document.createElement("span");
        now.className = "o_motion_qv_nowprice";
        now.textContent = this._money(data.price, cur);
        priceWrap.appendChild(now);
        info.appendChild(priceWrap);

        if (data.description) {
            const desc = document.createElement("p");
            desc.className = "o_motion_qv_desc";
            desc.textContent = data.description;
            info.appendChild(desc);
        }

        const actions = document.createElement("div");
        actions.className = "o_motion_qv_actions";

        if (data.has_variants || !data.variant_id) {
            const a = document.createElement("a");
            a.className = "btn btn-primary w-100";
            a.href = data.url || "/shop";
            a.textContent = "Voir le produit";
            actions.appendChild(a);
        } else {
            const add = document.createElement("button");
            add.type = "button";
            add.className = "btn btn-primary w-100";
            add.dataset.add = "1";
            add.dataset.variantId = data.variant_id;
            add.textContent = "Ajouter au panier";
            actions.appendChild(add);

            const a = document.createElement("a");
            a.className = "btn btn-link w-100 mt-1";
            a.href = data.url || "/shop";
            a.textContent = "Voir le produit";
            actions.appendChild(a);
        }
        info.appendChild(actions);

        this.content.appendChild(media);
        this.content.appendChild(info);
    }

    /* ---------- ajout au panier ---------- */

    onContentClick(ev) {
        const btn = ev.target.closest("[data-add]");
        if (!btn) {
            return;
        }
        ev.preventDefault();
        this._add(parseInt(btn.dataset.variantId, 10), btn);
    }

    async _add(variantId, btn) {
        if (this.adding || !variantId) {
            return;
        }
        this.adding = true;
        btn.disabled = true;
        const label = btn.textContent;
        btn.textContent = "Ajout…";
        try {
            await fetch("/shop/cart/update_json", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: { product_id: variantId, add_qty: 1 },
                }),
            });
            await this._refreshBadge();
            this.close();
        } catch {
            btn.disabled = false;
            btn.textContent = label;
        } finally {
            this.adding = false;
        }
    }

    async _refreshBadge() {
        try {
            const res = await fetch("/lolirine_motion/cart", {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await res.json();
            const badge = document.querySelector(".my_cart_quantity");
            if (badge && typeof data.count === "number") {
                badge.textContent = data.count;
            }
        } catch {
            /* no-op */
        }
    }

    destroy() {
        this.cards.forEach((card) => {
            const btn = card.querySelector(".o_motion_qv_btn");
            btn?.removeEventListener("click", this.onCardBtn);
        });
        document.body.style.overflow = "";
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.quickview", MotionQuickview);
