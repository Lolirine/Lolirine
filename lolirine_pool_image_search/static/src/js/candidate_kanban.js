/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";

/**
 * Vue kanban dédiée aux candidats images.
 *
 * Pas de comportement custom complexe pour l'instant — extension future
 * possible : swipe-to-reject sur mobile, raccourcis clavier (1=main, 2=gallery,
 * 3=reject), keyboard navigation entre cartes.
 *
 * Pour l'instant on enregistre simplement la classe JS pour permettre le
 * `js_class="pool_image_candidate_kanban"` dans la vue XML, ce qui permet
 * d'appliquer les styles SCSS spécifiques sans collision avec les autres
 * kanbans.
 */

class PoolImageCandidateKanbanRenderer extends KanbanRenderer {}

export const poolImageCandidateKanbanView = {
    ...kanbanView,
    Renderer: PoolImageCandidateKanbanRenderer,
};

registry.category("views").add("pool_image_candidate_kanban", poolImageCandidateKanbanView);
