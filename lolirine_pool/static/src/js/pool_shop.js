/**
 * Lolirine Pool - JavaScript Frontend
 * ====================================
 */

odoo.define('lolirine_pool.pool_shop', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    /**
     * Widget de recherche rapide avec autocomplétion
     */
    publicWidget.registry.PoolSearchAutocomplete = publicWidget.Widget.extend({
        selector: '.pool-search-autocomplete',
        events: {
            'input input[name="search"]': '_onSearchInput',
            'focus input[name="search"]': '_onSearchFocus',
            'blur input[name="search"]': '_onSearchBlur',
        },

        start: function () {
            this._super.apply(this, arguments);
            this.$input = this.$('input[name="search"]');
            this.$dropdown = null;
            this._searchTimeout = null;
        },

        _onSearchInput: function (ev) {
            const query = ev.target.value.trim();
            
            if (this._searchTimeout) {
                clearTimeout(this._searchTimeout);
            }

            if (query.length < 2) {
                this._hideDropdown();
                return;
            }

            this._searchTimeout = setTimeout(() => {
                this._fetchSuggestions(query);
            }, 300);
        },

        _onSearchFocus: function () {
            if (this.$dropdown && this.$dropdown.children().length > 0) {
                this.$dropdown.show();
            }
        },

        _onSearchBlur: function () {
            // Délai pour permettre le clic sur une suggestion
            setTimeout(() => {
                this._hideDropdown();
            }, 200);
        },

        _fetchSuggestions: async function (query) {
            try {
                const results = await ajax.jsonRpc('/shop/pool/autocomplete', 'call', {
                    query: query,
                    limit: 8
                });
                this._showDropdown(results);
            } catch (error) {
                console.error('Erreur autocomplétion:', error);
            }
        },

        _showDropdown: function (results) {
            if (!this.$dropdown) {
                this.$dropdown = $('<div class="pool-search-dropdown"></div>');
                this.$input.parent().append(this.$dropdown);
            }

            this.$dropdown.empty();

            if (results.length === 0) {
                this.$dropdown.append('<div class="p-3 text-muted">Aucun résultat</div>');
            } else {
                results.forEach(item => {
                    const $item = $(`
                        <a href="${item.url}" class="pool-search-item d-flex align-items-center p-2">
                            <img src="${item.image || '/web/image/product.template/' + item.id + '/image_128'}" 
                                 class="me-2" style="width: 40px; height: 40px; object-fit: contain;"/>
                            <div>
                                <div class="fw-bold">${item.name}</div>
                                <div class="text-primary">${item.price} €</div>
                            </div>
                        </a>
                    `);
                    this.$dropdown.append($item);
                });
            }

            this.$dropdown.show();
        },

        _hideDropdown: function () {
            if (this.$dropdown) {
                this.$dropdown.hide();
            }
        },
    });

    /**
     * Widget filtre de prix (range slider)
     */
    publicWidget.registry.PoolPriceFilter = publicWidget.Widget.extend({
        selector: '.pool-price-filter',
        events: {
            'input input[name="price_min"]': '_onPriceChange',
            'input input[name="price_max"]': '_onPriceChange',
            'click .btn-apply-filter': '_onApplyFilter',
        },

        start: function () {
            this._super.apply(this, arguments);
            this.$minInput = this.$('input[name="price_min"]');
            this.$maxInput = this.$('input[name="price_max"]');
            this.$minLabel = this.$('.price-min-label');
            this.$maxLabel = this.$('.price-max-label');
        },

        _onPriceChange: function () {
            const min = parseInt(this.$minInput.val()) || 0;
            const max = parseInt(this.$maxInput.val()) || 10000;
            
            this.$minLabel.text(min + ' €');
            this.$maxLabel.text(max + ' €');
        },

        _onApplyFilter: function () {
            const min = this.$minInput.val();
            const max = this.$maxInput.val();
            const currentUrl = new URL(window.location.href);
            
            currentUrl.searchParams.set('min_price', min);
            currentUrl.searchParams.set('max_price', max);
            
            window.location.href = currentUrl.toString();
        },
    });

    /**
     * Widget galerie d'images produit
     */
    publicWidget.registry.PoolProductGallery = publicWidget.Widget.extend({
        selector: '.pool-product-gallery',
        events: {
            'click .thumbnail': '_onThumbnailClick',
        },

        start: function () {
            this._super.apply(this, arguments);
            this.$mainImage = this.$('.main-image img');
            this.$thumbnails = this.$('.thumbnail');
        },

        _onThumbnailClick: function (ev) {
            const $thumb = $(ev.currentTarget);
            const newSrc = $thumb.data('full-image') || $thumb.find('img').attr('src');
            
            // Mettre à jour l'image principale
            this.$mainImage.attr('src', newSrc);
            
            // Mettre à jour la classe active
            this.$thumbnails.removeClass('active');
            $thumb.addClass('active');
        },
    });

    /**
     * Widget quantité avec +/-
     */
    publicWidget.registry.PoolQuantitySelector = publicWidget.Widget.extend({
        selector: '.pool-qty-selector',
        events: {
            'click .qty-minus': '_onMinus',
            'click .qty-plus': '_onPlus',
            'change input[name="add_qty"]': '_onQtyChange',
        },

        start: function () {
            this._super.apply(this, arguments);
            this.$input = this.$('input[name="add_qty"]');
            this.min = parseInt(this.$input.attr('min')) || 1;
            this.max = parseInt(this.$input.attr('max')) || 9999;
            this.step = parseInt(this.$input.attr('step')) || 1;
        },

        _onMinus: function () {
            let val = parseInt(this.$input.val()) || this.min;
            val = Math.max(this.min, val - this.step);
            this.$input.val(val).trigger('change');
        },

        _onPlus: function () {
            let val = parseInt(this.$input.val()) || this.min;
            val = Math.min(this.max, val + this.step);
            this.$input.val(val).trigger('change');
        },

        _onQtyChange: function () {
            let val = parseInt(this.$input.val()) || this.min;
            val = Math.max(this.min, Math.min(this.max, val));
            this.$input.val(val);
        },
    });

    /**
     * Widget comparateur de produits
     */
    publicWidget.registry.PoolProductCompare = publicWidget.Widget.extend({
        selector: '.pool-compare-widget',
        
        start: function () {
            this._super.apply(this, arguments);
            this.compareList = this._getCompareList();
            this._updateBadge();
        },

        _getCompareList: function () {
            const stored = sessionStorage.getItem('pool_compare');
            return stored ? JSON.parse(stored) : [];
        },

        _saveCompareList: function () {
            sessionStorage.setItem('pool_compare', JSON.stringify(this.compareList));
            this._updateBadge();
        },

        _updateBadge: function () {
            const $badge = this.$('.compare-badge');
            const count = this.compareList.length;
            
            if (count > 0) {
                $badge.text(count).show();
            } else {
                $badge.hide();
            }
        },

        addToCompare: function (productId) {
            if (this.compareList.length >= 4) {
                alert('Vous pouvez comparer maximum 4 produits');
                return false;
            }
            
            if (!this.compareList.includes(productId)) {
                this.compareList.push(productId);
                this._saveCompareList();
                return true;
            }
            return false;
        },

        removeFromCompare: function (productId) {
            const index = this.compareList.indexOf(productId);
            if (index > -1) {
                this.compareList.splice(index, 1);
                this._saveCompareList();
                return true;
            }
            return false;
        },

        clearCompare: function () {
            this.compareList = [];
            this._saveCompareList();
        },
    });

    /**
     * Animation ajout au panier
     */
    publicWidget.registry.PoolAddToCartAnimation = publicWidget.Widget.extend({
        selector: '.js_add_cart',
        events: {
            'click': '_onAddToCart',
        },

        _onAddToCart: function (ev) {
            const $btn = $(ev.currentTarget);
            const $productCard = $btn.closest('.pool-product-card');
            const $cartIcon = $('.o_wsale_my_cart');

            if ($productCard.length && $cartIcon.length) {
                // Créer un élément fantôme pour l'animation
                const $img = $productCard.find('.card-img-top').clone();
                $img.css({
                    position: 'fixed',
                    top: $productCard.offset().top - $(window).scrollTop(),
                    left: $productCard.offset().left,
                    width: $productCard.find('.card-img-top').width(),
                    height: $productCard.find('.card-img-top').height(),
                    zIndex: 9999,
                    borderRadius: '50%',
                    transition: 'all 0.8s ease-in-out',
                    opacity: 0.8,
                });

                $('body').append($img);

                // Animer vers le panier
                setTimeout(() => {
                    const cartPos = $cartIcon.offset();
                    $img.css({
                        top: cartPos.top - $(window).scrollTop(),
                        left: cartPos.left,
                        width: 30,
                        height: 30,
                        opacity: 0,
                    });
                }, 50);

                // Supprimer après animation
                setTimeout(() => {
                    $img.remove();
                }, 900);
            }
        },
    });

    /**
     * Lazy loading des images
     */
    publicWidget.registry.PoolLazyLoad = publicWidget.Widget.extend({
        selector: '.pool-shop',

        start: function () {
            this._super.apply(this, arguments);
            
            if ('IntersectionObserver' in window) {
                this._initLazyLoad();
            }
        },

        _initLazyLoad: function () {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            observer.unobserve(img);
                        }
                    }
                });
            }, {
                rootMargin: '50px',
            });

            this.$('img[data-src]').each((_, img) => {
                observer.observe(img);
            });
        },
    });

    return {
        PoolSearchAutocomplete: publicWidget.registry.PoolSearchAutocomplete,
        PoolPriceFilter: publicWidget.registry.PoolPriceFilter,
        PoolProductGallery: publicWidget.registry.PoolProductGallery,
        PoolQuantitySelector: publicWidget.registry.PoolQuantitySelector,
        PoolProductCompare: publicWidget.registry.PoolProductCompare,
        PoolAddToCartAnimation: publicWidget.registry.PoolAddToCartAnimation,
        PoolLazyLoad: publicWidget.registry.PoolLazyLoad,
    };
});
