/** @odoo-module **/

(function () {
    'use strict';

    if (!document.querySelector('.lw-page')) { return; }

    window.lolirineWishlist = {

        /* ── Filtrer par nom ──────────────────────────────── */
        filter: function (query) {
            var q = (query || '').toLowerCase().trim();
            var items = document.querySelectorAll('.lw-item');
            items.forEach(function (item) {
                var name = (item.dataset.name || '').toLowerCase();
                if (!q || name.indexOf(q) !== -1) {
                    item.classList.remove('lw-hidden');
                } else {
                    item.classList.add('lw-hidden');
                }
            });
        },

        /* ── Trier ────────────────────────────────────────── */
        sort: function (mode) {
            var list = document.getElementById('lw_product_list');
            if (!list) { return; }
            var items = Array.from(list.querySelectorAll('.lw-item'));
            items.sort(function (a, b) {
                if (mode === 'price_asc') {
                    return parseFloat(a.dataset.price || 0) - parseFloat(b.dataset.price || 0);
                }
                if (mode === 'price_desc') {
                    return parseFloat(b.dataset.price || 0) - parseFloat(a.dataset.price || 0);
                }
                if (mode === 'name') {
                    return (a.dataset.name || '').localeCompare(b.dataset.name || '');
                }
                /* date (défaut) : plus récent en premier */
                return (b.dataset.date || '').localeCompare(a.dataset.date || '');
            });
            items.forEach(function (item) { list.appendChild(item); });
        },

        /* ── Retirer un article ───────────────────────────── */
        remove: function (btn) {
            var wishId = btn.dataset.wishId;
            if (!wishId) { return; }
            fetch('/shop/wishlist/remove/' + wishId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                body: JSON.stringify({ csrf_token: odoo.csrf_token }),
            }).then(function () {
                var item = btn.closest('.lw-item');
                if (item) {
                    item.style.transition = 'opacity 0.2s';
                    item.style.opacity = '0';
                    setTimeout(function () {
                        item.remove();
                        window.lolirineWishlist._updateCount();
                    }, 220);
                }
            }).catch(function (e) {
                console.warn('[Wishlist] Remove error:', e);
                window.location.reload();
            });
        },

        /* ── Tout ajouter au panier ───────────────────────── */
        addAll: function () {
            var items = document.querySelectorAll('.lw-item:not(.lw-hidden)');
            var links = [];
            items.forEach(function (item) {
                var btn = item.querySelector('.lw-btn-cart');
                if (btn && btn.href) { links.push(btn.href); }
            });
            if (!links.length) { return; }
            /* Redirection vers la page panier après le dernier ajout */
            var done = 0;
            links.forEach(function (href) {
                fetch(href, { method: 'GET' }).then(function () {
                    done++;
                    if (done === links.length) {
                        window.location.href = '/shop/cart';
                    }
                });
            });
        },

        /* ── Partager la liste ────────────────────────────── */
        shareList: function () {
            var url = window.location.href;
            if (navigator.share) {
                navigator.share({
                    title: 'Ma liste de souhaits Lolirine Pool',
                    url: url,
                });
            } else if (navigator.clipboard) {
                navigator.clipboard.writeText(url).then(function () {
                    alert('Lien copié dans le presse-papier !');
                });
            } else {
                prompt('Copiez ce lien :', url);
            }
        },

        /* ── Mettre à jour le compteur dans le titre ─────── */
        _updateCount: function () {
            var remaining = document.querySelectorAll('.lw-item').length;
            var countEl = document.querySelector('.lw-count');
            if (countEl) {
                countEl.textContent = '(' + remaining + ' produit' + (remaining > 1 ? 's' : '') + ')';
            }
            /* Afficher la liste vide si besoin */
            if (remaining === 0) {
                window.location.reload();
            }
        },
    };

}());
