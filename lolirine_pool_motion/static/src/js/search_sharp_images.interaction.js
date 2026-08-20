/** @odoo-module **/
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

// Résultats de recherche : remplace les miniatures image_128 par image_256
// (plus nettes une fois agrandies dans la grille de cartes).
export class SearchResultSharpImages extends Interaction {
    static selector = "#wrap .o_search_result_item img";

    setup() {
        if (document.documentElement.dataset.websiteId !== "6") {
            return;
        }
        const src = this.el.getAttribute("src");
        if (src && src.includes("/image_128")) {
            this.el.setAttribute("src", src.replace("/image_128", "/image_256"));
        }
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.search_sharp_img", SearchResultSharpImages);
