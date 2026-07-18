/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/*
 * Barre d'achat collante (fiche produit).
 * Apparaît dès que le bouton "Ajouter au panier" natif sort de l'écran :
 * rappelle le nom + le prix (synchronisé avec la variante choisie) et
 * re-déclenche le VRAI bouton d'Odoo -> toute la logique variantes/panier
 * reste native, on ne duplique rien.
 */
export class MotionBuyBar extends Interaction {
    static selector = "#wrapwrap";

    setup() {
        this.bar = null;
        this.realBtn = null;
        this.priceSrc = null;
        this.observer = null;
        this.priceObserver = null;
        this.onBarClick = this.onBarClick.bind(this);
    }

    _findPriceSource() {
        return (
            document.querySelector(".oe_price .oe_currency_value") ||
            document.querySelector("#product_price .oe_currency_value") ||
            document.querySelector(".product_price .oe_currency_value") ||
            document.querySelector(".oe_currency_value")
        );
    }

    start() {
        if (document.documentElement.dataset.websiteId !== "6") {
            return;
        }
        this.realBtn =
            document.querySelector("#add_to_cart") ||
            document.querySelector("[name='add_to_cart']") ||
            document.querySelector("#product_detail a.js_check_product");
        if (!this.realBtn) {
            return; // pas une fiche produit
        }
        if (document.querySelector(".o_motion_buybar")) {
            return;
        }

        const nameEl = document.querySelector("#product_detail h1, h1[itemprop='name']");
        const imgEl = document.querySelector(
            "#o-carousel-product .carousel-item.active img, #product_detail img"
        );
        this.priceSrc = this._findPriceSource();

        const bar = document.createElement("div");
        bar.className = "o_motion_buybar";
        bar.innerHTML = `
            <div class="o_motion_buybar_inner">
                <img class="o_motion_buybar_img" alt=""/>
                <div class="o_motion_buybar_txt">
                    <span class="o_motion_buybar_name"></span>
                    <span class="o_motion_buybar_price"></span>
                </div>
                <button type="button" class="btn btn-primary o_motion_buybar_btn">
                    <i class="fa fa-shopping-cart me-1" aria-hidden="true"></i>Ajouter au panier
                </button>
            </div>`;
        document.body.appendChild(bar);
        this.bar = bar;

        if (imgEl && imgEl.src) {
            bar.querySelector(".o_motion_buybar_img").src = imgEl.src;
        } else {
            bar.querySelector(".o_motion_buybar_img").remove();
        }
        bar.querySelector(".o_motion_buybar_name").textContent =
            (nameEl?.textContent || "").trim();
        this._syncPrice();

        bar.querySelector(".o_motion_buybar_btn")
            .addEventListener("click", this.onBarClick);

        // Affiche la barre quand le bouton natif n'est plus visible.
        this.observer = new IntersectionObserver(
            (entries) => {
                for (const e of entries) {
                    this.bar?.classList.toggle("is-visible", !e.isIntersecting);
                }
            },
            { rootMargin: "0px 0px -10px 0px" }
        );
        this.observer.observe(this.realBtn);

        // Garde le prix à jour quand on change de variante.
        if (this.priceSrc) {
            this.priceObserver = new MutationObserver(() => this._syncPrice());
            this.priceObserver.observe(this.priceSrc, {
                childList: true,
                characterData: true,
                subtree: true,
            });
        }
    }

    _syncPrice() {
        if (!this.bar) {
            return;
        }
        const src = this.priceSrc || this._findPriceSource();
        const el = this.bar.querySelector(".o_motion_buybar_price");
        if (src && el) {
            el.textContent = (src.textContent || "").trim() + " €";
        }
    }

    onBarClick(ev) {
        ev.preventDefault();
        if (!this.realBtn) {
            return;
        }
        // Déclenche le vrai bouton d'Odoo (variante déjà sélectionnée dans le form).
        this.realBtn.click();
    }

    destroy() {
        this.observer?.disconnect();
        this.priceObserver?.disconnect();
        this.bar?.remove();
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.buybar", MotionBuyBar);
