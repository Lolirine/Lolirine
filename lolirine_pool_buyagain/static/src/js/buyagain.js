/** @odoo-module **/

(function () {

    // Langue de la page (/fr, /nl, /en) pour les textes posés par le script
    var LP_LANG = (document.documentElement.lang || 'fr').slice(0, 2).toLowerCase();
    var lpT = function (fr, nl, en) { return LP_LANG === 'nl' ? nl : (LP_LANG === 'en' ? en : fr); };
    'use strict';

    if (!document.querySelector('.ba-grid')) { return; }

    // ── Modifier la quantité ──────────────────────────
    window.baChangeQty = function (btn, delta) {
        var wrap = btn.closest('.ba-qty-wrap');
        var input = wrap.querySelector('.ba-qty-input');
        var val = parseInt(input.value, 10) || 1;
        val = Math.max(1, val + delta);
        input.value = val;

        // Mettre à jour le lien "Ajouter au panier"
        var footer = wrap.closest('.ba-card-footer');
        var cartBtn = footer.querySelector('.ba-btn-cart');
        if (cartBtn) {
            var pid = cartBtn.dataset.productId;
            if (pid) {
                cartBtn.href = '/shop/cart/update?product_id=' + pid + '&add_qty=' + val;
            }
        }
    };

    // ── Feedback visuel au clic "Ajouter au panier" ───
    document.querySelectorAll('.ba-btn-cart').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            var original = btn.textContent;
            btn.textContent = lpT('✓ Ajouté !', '✓ Toegevoegd!', '✓ Added!');
            btn.style.background = '#22c55e';
            setTimeout(function () {
                btn.textContent = original;
                btn.style.background = '';
            }, 1800);
        });
    });

}());
