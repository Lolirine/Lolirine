/** @odoo-module **/
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

// Autocomplétion (sidebar) : les vignettes sont recréées à chaque frappe.
// On observe le formulaire de recherche et on rehausse image_128 -> image_256.
export class SearchDropdownSharp extends Interaction {
    static selector = ".o_searchbar_form";

    setup() {
        if (document.documentElement.dataset.websiteId !== "6") {
            return;
        }
        this._bump = this._bump.bind(this);
        this.observer = new MutationObserver(this._bump);
        this.observer.observe(this.el, { childList: true, subtree: true });
    }

    _bump() {
        this.el.querySelectorAll("img[src*='/image_128']").forEach((img) => {
            img.setAttribute("src", img.getAttribute("src").replace("/image_128", "/image_256"));
        });
    }

    destroy() {
        this.observer?.disconnect();
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.search_dropdown_sharp", SearchDropdownSharp);
