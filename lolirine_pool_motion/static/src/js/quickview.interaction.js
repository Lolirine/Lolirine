/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

/*
 * Quickview produit (vague 2, option 2 : variantes).
 *
 *  - Loupe sur chaque carte (.oe_product) -> overlay centré.
 *  - Contenu depuis /lolirine_motion/product/<id> (image, prix, specs, attributs).
 *  - Produit à variantes : sélecteurs (pastilles / couleurs). À chaque changement,
 *    appel de la route OFFICIELLE /website_sale/get_combination_info pour
 *    recalculer prix / variante / image / dispo. Ajout via /shop/cart/update_json.
 *  - Produit simple : ajout direct. L'ajout met à jour le badge -> rebond + drawer.
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

        this.tmplId = null;
        this.currency = "EUR";
        this.currentVariantId = false;
        this.imgEl = null;
        this.priceNowEl = null;
        this.priceOldEl = null;
        this.addBtn = null;

        this.cards = [];
        this.onCardBtn = this.onCardBtn.bind(this);
    }

    start() {
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

    /* ---------- rpc ---------- */

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
        this.tmplId = data.id;
        this.currency = data.currency || "EUR";
        this.currentVariantId = data.variant_id || false;
        this.content.innerHTML = "";

        const media = document.createElement("div");
        media.className = "o_motion_qv_media";
        this.imgEl = document.createElement("img");
        this.imgEl.src = data.image_url;
        this.imgEl.alt = data.name;
        this.imgEl.loading = "lazy";
        media.appendChild(this.imgEl);

        const info = document.createElement("div");
        info.className = "o_motion_qv_info";

        const title = document.createElement("h3");
        title.className = "o_motion_qv_title";
        title.textContent = data.name;
        info.appendChild(title);

        const priceWrap = document.createElement("div");
        priceWrap.className = "o_motion_qv_price";
        this.priceOldEl = document.createElement("span");
        this.priceOldEl.className = "o_motion_qv_oldprice";
        if (data.has_discount) {
            this.priceOldEl.textContent = this._money(data.list_price, this.currency);
        } else {
            this.priceOldEl.style.display = "none";
        }
        this.priceNowEl = document.createElement("span");
        this.priceNowEl.className = "o_motion_qv_nowprice";
        this.priceNowEl.textContent = this._money(data.price, this.currency);
        priceWrap.appendChild(this.priceOldEl);
        priceWrap.appendChild(this.priceNowEl);
        info.appendChild(priceWrap);

        if (data.description) {
            const desc = document.createElement("p");
            desc.className = "o_motion_qv_desc";
            desc.textContent = data.description;
            info.appendChild(desc);
        }

        const hasAttrs = data.attributes && data.attributes.length;

        if (hasAttrs) {
            const wrap = document.createElement("div");
            wrap.className = "o_motion_qv_attrs";
            for (const attr of data.attributes) {
                const row = document.createElement("div");
                row.className = "o_motion_qv_attr";
                const lab = document.createElement("div");
                lab.className = "o_motion_qv_attr_label";
                lab.textContent = attr.name;
                const opts = document.createElement("div");
                opts.className = "o_motion_qv_opts";
                for (const v of attr.values) {
                    const pill = document.createElement("button");
                    pill.type = "button";
                    pill.className = "o_motion_qv_pill";
                    pill.dataset.ptav = v.id;
                    if (attr.display_type === "color" && v.color) {
                        pill.classList.add("is-color");
                        pill.style.backgroundColor = v.color;
                        pill.title = v.name;
                        pill.setAttribute("aria-label", v.name);
                    } else {
                        pill.textContent = v.name;
                    }
                    if ((data.default_combination || []).includes(v.id)) {
                        pill.classList.add("is-selected");
                    }
                    opts.appendChild(pill);
                }
                row.appendChild(lab);
                row.appendChild(opts);
                wrap.appendChild(row);
            }
            info.appendChild(wrap);
        }

        const actions = document.createElement("div");
        actions.className = "o_motion_qv_actions";

        if (data.variant_id) {
            this.addBtn = document.createElement("button");
            this.addBtn.type = "button";
            this.addBtn.className = "btn btn-primary w-100";
            this.addBtn.dataset.add = "1";
            this.addBtn.textContent = "Ajouter au panier";
            actions.appendChild(this.addBtn);

            const a = document.createElement("a");
            a.className = "btn btn-link w-100 mt-1";
            a.href = data.url || "/shop";
            a.textContent = "Voir le produit";
            actions.appendChild(a);
        } else {
            const a = document.createElement("a");
            a.className = "btn btn-primary w-100";
            a.href = data.url || "/shop";
            a.textContent = "Voir le produit";
            actions.appendChild(a);
        }
        info.appendChild(actions);

        this.content.appendChild(media);
        this.content.appendChild(info);

        if (hasAttrs) {
            this._recompute();
        }
    }

    /* ---------- variantes ---------- */

    _selectedPtavIds() {
        const ids = [];
        this.content.querySelectorAll(".o_motion_qv_attr").forEach((row) => {
            const sel = row.querySelector(".o_motion_qv_pill.is-selected");
            if (sel) {
                ids.push(parseInt(sel.dataset.ptav, 10));
            }
        });
        return ids;
    }

    async _recompute() {
        const ids = this._selectedPtavIds();
        try {
            const info = await this._rpc("/website_sale/get_combination_info", {
                product_template_id: this.tmplId,
                product_id: 0,
                combination: ids,
                add_qty: 1,
            });
            if (info.product_id) {
                this.currentVariantId = info.product_id;
                if (this.imgEl) {
                    this.imgEl.src =
                        "/web/image/product.product/" + info.product_id + "/image_512";
                }
            }
            if (this.priceNowEl && typeof info.price !== "undefined") {
                this.priceNowEl.textContent = this._money(info.price, this.currency);
            }
            if (this.priceOldEl) {
                if (info.list_price && info.price && info.list_price > info.price) {
                    this.priceOldEl.textContent = this._money(info.list_price, this.currency);
                    this.priceOldEl.style.display = "";
                } else {
                    this.priceOldEl.style.display = "none";
                }
            }
            if (this.addBtn) {
                const possible = info.is_combination_possible !== false;
                this.addBtn.disabled = !possible;
                this.addBtn.textContent = possible
                    ? "Ajouter au panier"
                    : "Combinaison indisponible";
            }
        } catch {
            // Repli : on garde la variante par défaut, prix figé.
        }
    }

    /* ---------- interactions contenu ---------- */

    onContentClick(ev) {
        const pill = ev.target.closest(".o_motion_qv_pill");
        if (pill) {
            ev.preventDefault();
            const row = pill.closest(".o_motion_qv_attr");
            row.querySelectorAll(".o_motion_qv_pill").forEach((p) =>
                p.classList.remove("is-selected")
            );
            pill.classList.add("is-selected");
            this._recompute();
            return;
        }
        const add = ev.target.closest("[data-add]");
        if (add) {
            ev.preventDefault();
            this._add(add);
        }
    }

    async _add(btn) {
        if (this.adding) {
            return;
        }
        if (!this.currentVariantId) {
            btn.textContent = "Variante non résolue";
            return;
        }
        this.adding = true;
        btn.disabled = true;
        if (!btn.dataset.label) {
            btn.dataset.label = btn.textContent;
        }
        btn.textContent = "Ajout…";
        try {
            const result = await this._rpc("/shop/cart/update", {
                line_id: false,
                product_id: this.currentVariantId,
                quantity: 1,
            });
            if (result === undefined || result === null) {
                throw new Error("réponse vide de update_cart");
            }
            await this._refreshBadge();
            btn.disabled = false;
            btn.textContent = btn.dataset.label;
            this.close();
        } catch (e) {
            btn.disabled = false;
            btn.textContent = "Erreur : " + (e.message || "ajout impossible");
            // eslint-disable-next-line no-console
            console.error("[quickview] ajout panier:", e, "variant=", this.currentVariantId);
            setTimeout(() => {
                btn.textContent = btn.dataset.label || "Ajouter au panier";
            }, 3000);
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
