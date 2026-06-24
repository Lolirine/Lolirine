/* Lolirine — Colisage
 * Cale le sélecteur de quantité de la fiche produit sur le colisage :
 *  - les boutons +/- avancent par pas de N (data-step) ;
 *  - une saisie manuelle est arrondie au multiple supérieur de N.
 * Le contrôle dur reste côté serveur (_verify_updated_quantity) ; ce script
 * n'est que la couche UX. Volontairement en JS classique (pas de dépendance).
 */
(function () {
    "use strict";

    function stepOf(input) {
        var s = parseInt(input.getAttribute("data-step") || "1", 10);
        return isNaN(s) || s < 1 ? 1 : s;
    }

    function roundUp(value, step) {
        if (!value || value < step) {
            return step;
        }
        return Math.ceil(value / step) * step;
    }

    // Saisie manuelle : on arrondit au multiple supérieur quand le champ perd le focus.
    document.addEventListener("change", function (ev) {
        var input = ev.target;
        if (!input.matches || !input.matches('input[name="add_qty"]')) {
            return;
        }
        var step = stepOf(input);
        if (step <= 1) {
            return;
        }
        var v = parseInt(input.value, 10);
        var snapped = roundUp(isNaN(v) ? step : v, step);
        if (snapped !== v) {
            input.value = snapped;
        }
    }, true);

    // Boutons +/- : on intercepte en phase de capture pour avancer par pas de N
    // avant le handler natif d'Odoo, puis on déclenche un "change" pour la MAJ.
    document.addEventListener("click", function (ev) {
        var btn = ev.target.closest && ev.target.closest(".css_quantity_minus, .css_quantity_plus");
        if (!btn) {
            return;
        }
        var wrap = btn.closest(".css_quantity");
        var input = wrap && wrap.querySelector('input[name="add_qty"]');
        if (!input) {
            return;
        }
        var step = stepOf(input);
        if (step <= 1) {
            return; // pas de colisage : on laisse le comportement natif
        }
        ev.preventDefault();
        ev.stopImmediatePropagation();
        var v = parseInt(input.value, 10);
        if (isNaN(v)) {
            v = step;
        }
        v = btn.classList.contains("css_quantity_plus") ? v + step : v - step;
        if (v < step) {
            v = step;
        }
        input.value = v;
        input.dispatchEvent(new Event("change", { bubbles: true }));
    }, true);
})();
