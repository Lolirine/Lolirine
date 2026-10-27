/** @odoo-module **/
/*
 * Correctif : un clic sur une pastille de couleur dans les filtres de la
 * boutique (/shop/category/...) levait « null is not an object (evaluating
 * 'parent.querySelectorAll') ». La méthode standard onChangeColorAttribute
 * cherche un conteneur produit (.js_product), qui n'existe que sur la fiche
 * produit, pas dans la colonne des filtres.
 * Dans les filtres : on surligne seulement la pastille ; le filtrage lui-même
 * est fait par le gestionnaire standard du formulaire (onChangeAttribute).
 */
import { patch } from "@web/core/utils/patch";
import { WebsiteSale } from "@website_sale/interactions/website_sale";

patch(WebsiteSale.prototype, {
    onChangeColorAttribute(ev) {
        if (!ev.target.closest(".js_product")) {
            ev.target.closest(".css_attribute_color")?.classList.toggle("active", ev.target.checked);
            return;
        }
        return super.onChangeColorAttribute(...arguments);
    },
});
