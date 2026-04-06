/** @odoo-module **/

(function () {
    'use strict';

    if (!document.querySelector('.lp-buypanel-delivery, .lp-trust-grid')) {
        return;
    }

    function getProductId() {
        var inp = document.querySelector('input[name="product_id"]');
        if (inp && inp.value) {
            return parseInt(inp.value, 10);
        }
        return null;
    }

    function jsonRpc(route, params) {
        return fetch(route, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: params }),
        }).then(function (r) {
            return r.json();
        }).then(function (d) {
            return d.result;
        });
    }

    function fillPanel(info) {
        if (!info) { return; }

        var delivery  = document.getElementById('lp_buypanel_delivery');
        var infoBlock = document.getElementById('lp_buypanel_info');

        if (delivery) {
            delivery.classList.remove('lp-stock-green', 'lp-stock-orange', 'lp-stock-gray');
            delivery.classList.add(info.stock_class || 'lp-stock-green');

            var stockLabel = delivery.querySelector('.lp-stock-label');
            var stockSub   = delivery.querySelector('.lp-stock-sub');
            if (stockLabel) { stockLabel.textContent = info.stock_label || ''; }
            if (stockSub)   { stockSub.textContent = info.stock_qty > 0 ? '— expédié sous 24h' : ''; }

            var delivText = delivery.querySelector('.lp-delivery-text');
            if (delivText) {
                delivText.innerHTML = 'Livraison estimée : <strong>' + (info.delivery || '') + '</strong>';
            }
            delivery.style.display = '';
        }

        if (infoBlock) {
            if (info.default_code) {
                var refRow = infoBlock.querySelector('.lp-info-ref');
                var refVal = infoBlock.querySelector('.lp-val-ref');
                if (refRow) { refRow.style.display = ''; }
                if (refVal) { refVal.textContent = info.default_code; }
            }
            if (info.brand) {
                var brandRow = infoBlock.querySelector('.lp-info-brand');
                var brandVal = infoBlock.querySelector('.lp-val-brand');
                if (brandRow) { brandRow.style.display = ''; }
                if (brandVal) { brandVal.textContent = info.brand; }
            }
            if (info.warranty) {
                var warRow = infoBlock.querySelector('.lp-info-warranty');
                var warVal = infoBlock.querySelector('.lp-val-warranty');
                if (warRow) { warRow.style.display = ''; }
                if (warVal) { warVal.textContent = info.warranty; }
                var wLabel = document.querySelector('.lp-warranty-label');
                if (wLabel) { wLabel.textContent = 'Garantie ' + info.warranty; }
            }
            var delivCell = infoBlock.querySelector('.lp-val-delivery');
            if (delivCell) {
                if (info.free_delivery) {
                    delivCell.innerHTML = 'Offerte <span class="lp-free-delivery-badge">GRATUITE</span>';
                } else {
                    delivCell.textContent = 'Offerte dès 499 € HT';
                }
            }
            infoBlock.style.display = '';
        }
    }

    function loadPanelInfo(productId) {
        if (!productId) { return; }
        jsonRpc('/shop/buypanel/info', { product_id: productId })
            .then(fillPanel)
            .catch(function (e) { console.warn('[LolirinePanel] Erreur:', e); });
    }

    function init() {
        function tryLoad(attempts) {
            var pid = getProductId();
            if (pid) {
                loadPanelInfo(pid);
            } else if (attempts > 0) {
                setTimeout(function () { tryLoad(attempts - 1); }, 300);
            }
        }
        tryLoad(10);

        document.addEventListener('change', function (e) {
            var tgt = e.target;
            var sel = tgt && tgt.closest
                ? tgt.closest('select.js_variant_change, input.js_variant_change')
                : null;
            if (!sel) { return; }
            setTimeout(function () {
                var newId = getProductId();
                if (newId) { loadPanelInfo(newId); }
            }, 300);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

}());
