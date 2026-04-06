/** @odoo-module **/
/**
 * Lolirine Pool – Buy Panel JS
 * Charge les infos dynamiques (stock, livraison, marque, garantie)
 * depuis le controller Python et les injecte dans le DOM.
 */

(function () {
    'use strict';

    // ─── N'agir que sur le Pool Store ─────────────────────────
    if (!document.querySelector('.lp-buypanel-delivery')) return;

    // ─── Récupérer le product_id depuis la page ───────────────
    function getProductId() {
        // Odoo 19 - le form n'a plus de classe spécifique
        const inp = document.querySelector(
            'input[name="product_id"], ' +
            '.js_product input[name="product_id"], ' +
            'form input[name="product_id"]'
        );
        return inp ? parseInt(inp.value, 10) : null;
    }

    // ─── Helper JSON-RPC ──────────────────────────────────────
    async function jsonRpc(route, params) {
        const res = await fetch(route, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params }),
        });
        const data = await res.json();
        return data.result;
    }

    // ─── Remplir les éléments du DOM ──────────────────────────
    function fillPanel(info) {
        if (!info) return;

        const delivery = document.getElementById('lp_buypanel_delivery');
        const infoBlock = document.getElementById('lp_buypanel_info');

        if (!delivery) return;

        // ── Stock ──────────────────────────────────────────────
        delivery.classList.remove('lp-stock-green', 'lp-stock-orange', 'lp-stock-gray');
        delivery.classList.add(info.stock_class || 'lp-stock-green');

        const stockLabel = delivery.querySelector('.lp-stock-label');
        const stockSub   = delivery.querySelector('.lp-stock-sub');
        if (stockLabel) stockLabel.textContent = info.stock_label || '';
        if (stockSub) {
            stockSub.textContent = info.stock_qty > 0 ? '— expédié sous 24h' : '';
        }

        // ── Livraison ──────────────────────────────────────────
        const delivText = delivery.querySelector('.lp-delivery-text');
        if (delivText) {
            delivText.innerHTML = `Livraison estimée : <strong>${info.delivery || ''}</strong>`;
        }

        delivery.style.display = '';

        // ── Infos produit ──────────────────────────────────────
        if (!infoBlock) return;

        if (info.default_code) {
            infoBlock.querySelector('.lp-info-ref').style.display = '';
            infoBlock.querySelector('.lp-val-ref').textContent = info.default_code;
        }

        if (info.brand) {
            infoBlock.querySelector('.lp-info-brand').style.display = '';
            infoBlock.querySelector('.lp-val-brand').textContent = info.brand;
        }

        if (info.warranty) {
            infoBlock.querySelector('.lp-info-warranty').style.display = '';
            infoBlock.querySelector('.lp-val-warranty').textContent = info.warranty;

            // Mettre à jour le badge garantie dans les trust badges
            const warrantyLabel = document.querySelector('.lp-warranty-label');
            if (warrantyLabel) {
                warrantyLabel.textContent = `Garantie ${info.warranty}`;
            }
        }

        // Livraison offerte
        const delivCell = infoBlock.querySelector('.lp-val-delivery');
        if (delivCell) {
            if (info.free_delivery) {
                delivCell.innerHTML = 'Offerte <span class="lp-free-delivery-badge">GRATUITE</span>';
            } else {
                delivCell.textContent = 'Offerte dès 499 € HT';
            }
        }

        infoBlock.style.display = '';
    }

    // ─── Charger les infos pour un product_id ─────────────────
    async function loadPanelInfo(productId) {
        if (!productId) return;
        try {
            const info = await jsonRpc('/shop/buypanel/info', { product_id: productId });
            fillPanel(info);
        } catch (e) {
            console.warn('[LolirinePanel] Erreur chargement infos:', e);
        }
    }

    // ─── Init au chargement de la page ────────────────────────
    function init() {
        const productId = getProductId();
        if (productId) {
            loadPanelInfo(productId);
        }

        // ─ Rechargement si variante changée ─────────────────
        // Odoo déclenche "variant_change" sur le formulaire configurateur
        document.addEventListener('change', function (e) {
            const sel = e.target.closest('select.js_variant_change, input.js_variant_change');
            if (!sel) return;
            // Petit délai pour laisser Odoo mettre à jour le champ product_id
            setTimeout(() => {
                const newId = getProductId();
                if (newId) loadPanelInfo(newId);
            }, 200);
        });

        // ─ Observer les mutations sur le champ product_id ───
        const form = document.querySelector('form.js_add_cart_json, form[action="/shop/cart/update"]');
        if (form) {
            const observer = new MutationObserver(() => {
                const newId = getProductId();
                if (newId) loadPanelInfo(newId);
            });
            const inp = form.querySelector('input[name="product_id"]');
            if (inp) {
                observer.observe(inp, { attributes: true, attributeFilter: ['value'] });
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
