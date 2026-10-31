/** @odoo-module **/
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

// Méga-menus du Pool Store : le survol ouvre le panneau (comportement natif
// « sous-menus au survol ») et le CLIC sur le titre ouvre la page de la rubrique
// (URL du menu, exposée par le template dans data-lp-href).
// Sur écran tactile et dans l'en-tête mobile, le clic garde son rôle natif
// (ouvrir / fermer le panneau), sinon le panneau serait inaccessible.
export class MegaMenuLink extends Interaction {
    static selector = "header#top";
    dynamicContent = {
        ".o_mega_menu_toggle[data-lp-href]": {
            "t-on-click.withTarget": this.onClick,
        },
    };

    onClick(ev, toggleEl) {
        if (document.documentElement.dataset.websiteId !== "6") {
            return;
        }
        if (toggleEl.closest(".o_header_mobile")) {
            return;
        }
        if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
            return;
        }
        const href = toggleEl.dataset.lpHref;
        if (!href || href === "#") {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        if (ev.ctrlKey || ev.metaKey) {
            window.open(href, "_blank");
        } else {
            window.location.href = href;
        }
    }
}

registry.category("public.interactions").add("lolirine_pool_motion.mega_menu_link", MegaMenuLink);
