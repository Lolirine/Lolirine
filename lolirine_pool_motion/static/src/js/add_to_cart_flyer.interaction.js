/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getMotion, prefersReducedMotion } from "./motion_helpers";

/*
 * Flyer "ajout au panier" : une copie de l'image produit vole vers l'icône panier,
 * puis le badge du panier fait un petit pop.
 *
 * 100 % VISUEL : on n'appelle jamais preventDefault, on ne touche pas au flux Odoo.
 * Odoo gère l'ajout réel ; on ne fait que l'effet par-dessus.
 *
 * Cible : le bouton principal de la fiche produit (#add_to_cart) et tout
 * bouton explicitement marqué [data-motion-flyer] (ex. add rapide en grille).
 * On évite volontairement .js_add_cart_json (utilisé aussi par les +/- quantité).
 */
export class MotionAddToCartFlyer extends Interaction {
    static selector = "#add_to_cart, [data-motion-flyer]";

    dynamicContent = {
        // pointerdown : déclenché tôt, avant la navigation/submit éventuels.
        _root: { "t-on-pointerdown": this.fly },
    };

    setup() {
        this.motion = getMotion();
        this.reduced = prefersReducedMotion();
    }

    _findImage() {
        // Fiche produit puis grille, avec plusieurs candidats robustes.
        const inCard = this.el.closest(".oe_product");
        if (inCard) {
            const img = inCard.querySelector("img");
            if (img) {
                return img;
            }
        }
        return document.querySelector(
            "#o-carousel-product img.product_detail_img," +
                "#o-carousel-product .carousel-item.active img," +
                "img.product_detail_img," +
                "#product_detail img"
        );
    }

    _findCart() {
        return document.querySelector(
            ".my_cart_quantity," +
                ".o_wsale_my_cart," +
                'header#top a[href$="/shop/cart"]'
        );
    }

    fly() {
        if (!this.motion || this.reduced) {
            return;
        }
        const img = this._findImage();
        const cart = this._findCart();
        if (!img || !cart) {
            return;
        }

        const from = img.getBoundingClientRect();
        const to = cart.getBoundingClientRect();
        if (!from.width || !to.width) {
            return;
        }

        const clone = img.cloneNode(true);
        Object.assign(clone.style, {
            position: "fixed",
            left: `${from.left}px`,
            top: `${from.top}px`,
            width: `${from.width}px`,
            height: `${from.height}px`,
            margin: "0",
            borderRadius: "12px",
            objectFit: "cover",
            pointerEvents: "none",
            zIndex: "2000",
            boxShadow: "0 10px 30px rgba(0,0,0,.25)",
        });
        clone.classList.add("o_motion_flyer");
        document.body.appendChild(clone);

        const dx = to.left + to.width / 2 - (from.left + from.width / 2);
        const dy = to.top + to.height / 2 - (from.top + from.height / 2);

        this.motion
            .animate(
                clone,
                {
                    x: [0, dx * 0.5, dx],
                    y: [0, dy - 120, dy], // arc : monte un peu avant de plonger
                    scale: [1, 0.6, 0.12],
                    opacity: [1, 1, 0.2],
                },
                { duration: 0.8, ease: [0.16, 1, 0.3, 1] }
            )
            .finished?.then(() => {
                clone.remove();
                this._pulseCart();
            });
    }

    _pulseCart() {
        const badge = document.querySelector(".my_cart_quantity");
        if (!badge || !this.motion) {
            return;
        }
        this.motion.animate(
            badge,
            { scale: [1, 1.5, 1] },
            { duration: 0.45, ease: [0.34, 1.56, 0.64, 1] }
        );
    }
}

registry
    .category("public.interactions")
    .add("lolirine_pool_motion.add_to_cart_flyer", MotionAddToCartFlyer);
