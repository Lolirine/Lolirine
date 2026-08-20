/** @odoo-module **/
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

// Corrige le data-limit=0 de la barre de recherche (sidebar Pool Store),
// qui désactive l'autocomplétion. On remet une limite avant l'init d'Odoo.
export class SearchLimitFix extends Interaction {
    static selector = ".o_searchbar_form input[name='search']";

    setup() {
        if (document.documentElement.dataset.websiteId !== "6") {
            return;
        }
        const lim = this.el.getAttribute("data-limit");
        if (!lim || parseInt(lim, 10) < 1) {
            this.el.setAttribute("data-limit", "5");
        }
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.search_limit_fix", SearchLimitFix);
