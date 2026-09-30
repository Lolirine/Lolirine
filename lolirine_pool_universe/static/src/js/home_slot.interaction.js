/** @odoo-module **/
/**
 * Blocs d'accueil déplaçables (vitrine, tuiles, petits prix).
 *
 * Le bloc posé dans la page ne contient qu'un repère vide ; le contenu est
 * chargé ici, sur le site publié uniquement. Les interactions ne tournent pas
 * en mode édition, et destroy() vide le contenu avant l'ouverture de l'éditeur :
 * rien de généré n'est donc jamais enregistré dans la page (leçon du chat IA).
 */
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PoolUniverseHomeSlot extends Interaction {
    static selector = ".s_pu_home_slot";

    async willStart() {
        this.html = "";
        const block = this.el.dataset.puBlock;
        if (!block || document.body.classList.contains("editor_enable")) {
            return;
        }
        try {
            const response = await this.waitFor(
                fetch(`/lolirine_universe/home_block/${encodeURIComponent(block)}`, {
                    credentials: "same-origin",
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                })
            );
            if (response.ok) {
                this.html = (await this.waitFor(response.text())).trim();
            }
        } catch {
            this.html = "";
        }
    }

    start() {
        this.target = this.el.querySelector(".s_pu_slot_content");
        if (!this.target) {
            return;
        }
        if (this.html) {
            this.target.innerHTML = this.html;
            this.el.classList.add("s_pu_slot_loaded");
        } else {
            this.el.classList.add("s_pu_slot_empty");
        }
    }

    destroy() {
        if (this.target) {
            this.target.innerHTML = "";
        }
        this.el.classList.remove("s_pu_slot_loaded", "s_pu_slot_empty");
    }
}

registry
    .category("public.interactions")
    .add("lolirine_pool_universe.home_slot", PoolUniverseHomeSlot);
