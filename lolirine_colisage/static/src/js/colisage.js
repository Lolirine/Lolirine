/* Lolirine — Colisage
 * 1) Cale le sélecteur de quantité sur le colisage (pas de N, arrondi saisie).
 * 2) Insère la mention "Vendu par colis de N" juste au-dessus de l'input
 *    quantité réel, dans la colonne produit (compatible buy panel custom).
 * Le contrôle dur reste serveur (_verify_updated_quantity) ; ceci est l'UX.
 * JS classique volontaire (aucune dépendance Odoo).
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

    // --- 1a) Saisie manuelle : arrondi au multiple supérieur ---
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

    // --- 1b) Boutons +/- : avancer par pas de N ---
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
            return; // pas de colisage : comportement natif
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

    // --- 2) Mention "Vendu par colis de N" au-dessus de l'input quantité ---
    function injectNotices() {
        var inputs = document.querySelectorAll(
            '#o_wsale_product_details_content input[name="add_qty"]'
        );
        if (!inputs.length) {
            inputs = document.querySelectorAll('input[name="add_qty"]');
        }
        if (!inputs.length) {
            return false; // pas encore rendu, on réessaiera
        }
        inputs.forEach(function (input) {
            if (input.dataset.colisageNoticed) {
                return;
            }
            var step = stepOf(input);
            if (step <= 1) {
                input.dataset.colisageNoticed = "1";
                return;
            }
            var anchor = input.closest("#o_wsale_cta_wrapper")
                || input.closest("#add_to_cart_wrap")
                || input.closest(".css_quantity");
            if (!anchor || !anchor.parentNode) {
                return;
            }
            var note = document.createElement("div");
            note.className =
                "o_colisage_notice alert alert-info py-2 px-3 mb-3 w-100 d-flex align-items-center";
            note.setAttribute("role", "status");
            note.innerHTML =
                '<i class="fa fa-cubes me-2"></i><span>Vendu par colis de '
                + step
                + " pièces — la quantité s'ajuste par multiples de "
                + step
                + ".</span>";
            anchor.parentNode.insertBefore(note, anchor);
            input.dataset.colisageNoticed = "1";
        });
        return true;
    }

    function onReady(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    onReady(function () {
        if (injectNotices()) {
            return;
        }
        var tries = 0;
        var iv = setInterval(function () {
            tries += 1;
            if (injectNotices() || tries > 12) {
                clearInterval(iv);
            }
        }, 300);
    });
})();
