/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

/**
 * Widget principal pour les sections de recommandations
 * Compatible Odoo 19
 */
publicWidget.registry.HomepageRecommendations = publicWidget.Widget.extend({
    selector: '.s_recommendations_section',
    disabledInEditableMode: true,
    
    /**
     * @override
     */
    start() {
        this._super.apply(this, arguments);
        this.carousel = this.el.querySelector('.recommendations-carousel');
        this.productsContainer = this.el.querySelector('.recommendations-products');
        this.skeleton = this.el.querySelector('.recommendations-skeleton');
        
        if (!this.carousel) return Promise.resolve();
        
        // Récupérer la configuration
        this.sectionType = this.carousel.dataset.sectionType || 'best_sellers';
        this.limit = parseInt(this.carousel.dataset.limit) || 12;
        this.categoryId = this.carousel.dataset.categoryId ? parseInt(this.carousel.dataset.categoryId) : null;
        this.hideIfEmpty = this.carousel.dataset.hideIfEmpty === 'true';
        this.showDiscount = this.carousel.dataset.showDiscount === 'true';
        this.showBadge = this.carousel.dataset.showBadge || '';
        this.requireLogin = this.carousel.dataset.requireLogin === 'true';
        
        // Charger les recommandations
        this._loadRecommendations();
        
        // Initialiser le carrousel
        this._initCarousel();
        
        return Promise.resolve();
    },
    
    /**
     * Charge les recommandations depuis le serveur
     */
    async _loadRecommendations() {
        try {
            const result = await rpc('/shop/recommendations', {
                section: this.sectionType,
                limit: this.limit,
                category_id: this.categoryId,
            });
            
            if (result.success && result.products.length > 0) {
                this._renderProducts(result.products, result);
                this._hideSkeleton();
            } else if (this.hideIfEmpty) {
                this._hideSection();
            } else {
                this._showEmptyState();
            }
        } catch (error) {
            console.error('Erreur chargement recommandations:', error);
            if (this.hideIfEmpty) {
                this._hideSection();
            } else {
                this._showErrorState();
            }
        }
    },
    
    /**
     * Génère le HTML des produits
     */
    _renderProducts(products, metadata) {
        let html = '';
        
        products.forEach(product => {
            html += this._renderProductCard(product, metadata);
        });
        
        this.productsContainer.innerHTML = html;
        
        // Mettre à jour le titre si fourni par le serveur
        if (metadata.title) {
            const titleEl = this.el.querySelector('.title-text');
            if (titleEl) {
                titleEl.textContent = metadata.title;
            }
        }
        
        // Mettre à jour le sous-titre
        if (metadata.subtitle) {
            const subtitleEl = this.el.querySelector('.recommendations-subtitle');
            if (subtitleEl) {
                subtitleEl.textContent = metadata.subtitle;
                subtitleEl.style.display = 'block';
            }
        }
        
        // Ajouter les event listeners
        this._bindProductEvents();
    },
    
    /**
     * Génère le HTML d'une carte produit
     */
    _renderProductCard(product, metadata) {
        const priceFormatted = this._formatPrice(product.price, product.currency_symbol, product.currency_position);
        const oldPriceFormatted = product.has_discount ? 
            this._formatPrice(product.compare_list_price, product.currency_symbol, product.currency_position) : '';
        
        let badgeHtml = '';
        if (this.showBadge) {
            badgeHtml = `<span class="recommendation-badge bg-primary">${this.showBadge}</span>`;
        } else if (this.showDiscount && product.has_discount && product.discount_pct > 0) {
            badgeHtml = `<span class="recommendation-badge discount-badge bg-danger">-${product.discount_pct}%</span>`;
        }
        
        // Étoiles de notation
        let ratingHtml = '';
        if (product.rating_count > 0) {
            let stars = '';
            for (let i = 0; i < 5; i++) {
                const starClass = i < Math.round(product.rating) ? 'fa-star text-warning' : 'fa-star-o text-muted';
                stars += `<i class="fa ${starClass}"></i>`;
            }
            ratingHtml = `
                <div class="recommendation-rating">
                    <span class="rating-stars">${stars}</span>
                    <span class="rating-count text-muted">(${product.rating_count})</span>
                </div>
            `;
        }
        
        // Prix barré si réduction
        let priceHtml = `<span class="current-price">${priceFormatted}</span>`;
        if (product.has_discount && oldPriceFormatted) {
            priceHtml += `<span class="old-price text-muted text-decoration-line-through ms-2">${oldPriceFormatted}</span>`;
        }
        
        // Stock
        const stockClass = product.in_stock ? 'in-stock' : 'out-of-stock';
        const stockText = product.in_stock ? '' : '<span class="out-of-stock-label text-danger small">Rupture</span>';
        
        return `
            <div class="recommendation-card ${stockClass}" data-product-id="${product.id}">
                <a href="${product.url}" class="recommendation-card-link">
                    <div class="recommendation-card-image">
                        <img src="${product.image_url}" 
                             alt="${this._escapeHtml(product.name)}"
                             loading="lazy"
                             class="img-fluid"/>
                        ${badgeHtml}
                    </div>
                    <div class="recommendation-card-body">
                        <h6 class="recommendation-card-title">${this._escapeHtml(product.name)}</h6>
                        ${ratingHtml}
                        <div class="recommendation-price">
                            ${priceHtml}
                        </div>
                        ${stockText}
                    </div>
                </a>
                <div class="recommendation-card-actions">
                    <button type="button" 
                            class="btn btn-sm btn-primary add-to-cart-quick" 
                            data-product-id="${product.id}"
                            ${!product.in_stock ? 'disabled' : ''}
                            title="Ajouter au panier">
                        <i class="fa fa-cart-plus"></i>
                    </button>
                    <button type="button" 
                            class="btn btn-sm btn-outline-secondary add-to-wishlist" 
                            data-product-id="${product.id}"
                            title="Ajouter aux favoris">
                        <i class="fa fa-heart-o"></i>
                    </button>
                </div>
            </div>
        `;
    },
    
    /**
     * Formate un prix avec le symbole de devise
     */
    _formatPrice(price, symbol, position) {
        const formattedPrice = price.toFixed(2).replace('.', ',');
        if (position === 'before') {
            return `${symbol}${formattedPrice}`;
        }
        return `${formattedPrice} ${symbol}`;
    },
    
    /**
     * Échappe le HTML pour éviter les XSS
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    /**
     * Initialise les contrôles du carrousel
     */
    _initCarousel() {
        const prevBtn = this.el.querySelector('.carousel-prev');
        const nextBtn = this.el.querySelector('.carousel-next');
        const carousel = this.carousel;
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => this._scrollCarousel(-1));
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this._scrollCarousel(1));
        }
        
        // Vérifier les boutons au scroll
        carousel.addEventListener('scroll', () => this._updateNavButtons());
        
        // Initialiser l'état des boutons
        setTimeout(() => this._updateNavButtons(), 100);
    },
    
    /**
     * Scroll le carrousel
     */
    _scrollCarousel(direction) {
        const cardWidth = this.productsContainer.querySelector('.recommendation-card')?.offsetWidth || 200;
        const gap = 16;
        const scrollAmount = (cardWidth + gap) * 3;
        
        this.carousel.scrollBy({
            left: direction * scrollAmount,
            behavior: 'smooth'
        });
    },
    
    /**
     * Met à jour l'état des boutons de navigation
     */
    _updateNavButtons() {
        const prevBtn = this.el.querySelector('.carousel-prev');
        const nextBtn = this.el.querySelector('.carousel-next');
        
        if (prevBtn) {
            prevBtn.classList.toggle('disabled', this.carousel.scrollLeft <= 0);
        }
        
        if (nextBtn) {
            const maxScroll = this.carousel.scrollWidth - this.carousel.clientWidth;
            nextBtn.classList.toggle('disabled', this.carousel.scrollLeft >= maxScroll - 5);
        }
    },
    
    /**
     * Bind les événements sur les produits
     */
    _bindProductEvents() {
        // Ajout rapide au panier
        this.productsContainer.querySelectorAll('.add-to-cart-quick').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                const productId = parseInt(btn.dataset.productId);
                await this._addToCart(productId);
            });
        });
        
        // Ajout aux favoris
        this.productsContainer.querySelectorAll('.add-to-wishlist').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                const productId = parseInt(btn.dataset.productId);
                await this._addToWishlist(productId, btn);
            });
        });
    },
    
    /**
     * Ajoute un produit au panier
     */
    async _addToCart(productId) {
        try {
            await rpc('/shop/cart/update_json', {
                product_id: productId,
                add_qty: 1,
            });
            
            // Mettre à jour le compteur du panier
            const cartIcon = document.querySelector('.my_cart_quantity');
            if (cartIcon) {
                const currentQty = parseInt(cartIcon.textContent) || 0;
                cartIcon.textContent = currentQty + 1;
            }
            
            // Notification
            this._showNotification('Produit ajouté au panier', 'success');
        } catch (error) {
            console.error('Erreur ajout panier:', error);
            this._showNotification('Erreur lors de l\'ajout au panier', 'danger');
        }
    },
    
    /**
     * Ajoute un produit aux favoris
     */
    async _addToWishlist(productId, btn) {
        try {
            await rpc('/shop/wishlist/add', {
                product_id: productId,
            });
            
            // Changer l'icône
            const icon = btn.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-heart-o');
                icon.classList.add('fa-heart', 'text-danger');
            }
            
            this._showNotification('Produit ajouté aux favoris', 'success');
        } catch (error) {
            console.error('Erreur ajout wishlist:', error);
            this._showNotification('Erreur lors de l\'ajout aux favoris', 'danger');
        }
    },
    
    /**
     * Affiche une notification toast
     */
    _showNotification(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast-notification alert alert-${type}`;
        toast.innerHTML = `
            <i class="fa ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} me-2"></i>
            ${message}
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },
    
    /**
     * Cache le skeleton loader
     */
    _hideSkeleton() {
        if (this.skeleton) {
            this.skeleton.style.display = 'none';
        }
    },
    
    /**
     * Cache toute la section
     */
    _hideSection() {
        this.el.style.display = 'none';
    },
    
    /**
     * Affiche un état vide
     */
    _showEmptyState() {
        this._hideSkeleton();
        this.productsContainer.innerHTML = `
            <div class="empty-state text-center py-4">
                <i class="fa fa-inbox fa-3x text-muted mb-3"></i>
                <p class="text-muted">Aucun produit à afficher pour le moment</p>
            </div>
        `;
    },
    
    /**
     * Affiche un état d'erreur
     */
    _showErrorState() {
        this._hideSkeleton();
        this.productsContainer.innerHTML = `
            <div class="error-state text-center py-4">
                <i class="fa fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                <p class="text-muted">Impossible de charger les recommandations</p>
            </div>
        `;
    },
});

/**
 * Widget pour la grille de catégories préférées
 */
publicWidget.registry.PreferredCategories = publicWidget.Widget.extend({
    selector: '.s_preferred_categories',
    disabledInEditableMode: true,
    
    start() {
        this._super.apply(this, arguments);
        this.grid = this.el.querySelector('.preferred-categories-grid');
        this.content = this.el.querySelector('.categories-content');
        this.skeleton = this.el.querySelector('.categories-skeleton');
        
        if (!this.grid) return Promise.resolve();
        
        this.limit = parseInt(this.grid.dataset.limit) || 6;
        
        this._loadCategories();
        return Promise.resolve();
    },
    
    async _loadCategories() {
        try {
            const result = await rpc('/shop/preferences/categories', {
                limit: this.limit,
            });
            
            if (result.success && result.categories.length > 0) {
                this._renderCategories(result.categories);
            } else {
                // Charger les catégories principales par défaut
                await this._loadDefaultCategories();
            }
            
            this._hideSkeleton();
        } catch (error) {
            console.error('Erreur chargement catégories:', error);
            await this._loadDefaultCategories();
        }
    },
    
    async _loadDefaultCategories() {
        try {
            // Utiliser les catégories principales du shop
            const result = await rpc('/shop/categories', {
                limit: this.limit,
            });
            
            if (result && result.length > 0) {
                this._renderCategories(result);
            }
        } catch (error) {
            console.error('Erreur chargement catégories par défaut:', error);
        }
    },
    
    _renderCategories(categories) {
        let html = '';
        
        categories.forEach(cat => {
            html += `
                <div class="col-6 col-md-4 col-lg-2">
                    <a href="/shop/category/${cat.id}" class="category-card">
                        <div class="category-image">
                            <img src="${cat.image_url}" alt="${this._escapeHtml(cat.name)}" loading="lazy"/>
                        </div>
                        <span class="category-name">${this._escapeHtml(cat.name)}</span>
                    </a>
                </div>
            `;
        });
        
        this.content.innerHTML = html;
    },
    
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    _hideSkeleton() {
        if (this.skeleton) {
            this.skeleton.style.display = 'none';
        }
    },
});

/**
 * Widget pour tracker les vues de produits
 */
publicWidget.registry.ProductViewTracker = publicWidget.Widget.extend({
    selector: '[data-track-view="true"]',
    disabledInEditableMode: true,
    
    start() {
        this._super.apply(this, arguments);
        const productId = this.el.dataset.productId;
        
        if (productId) {
            this._trackView(parseInt(productId));
        }
        return Promise.resolve();
    },
    
    async _trackView(productId) {
        try {
            await rpc('/shop/track/view', {
                product_id: productId,
            });
        } catch (error) {
            // Silently fail - tracking shouldn't break the page
            console.warn('Erreur tracking vue produit:', error);
        }
    },
});

export default {
    HomepageRecommendations: publicWidget.registry.HomepageRecommendations,
    PreferredCategories: publicWidget.registry.PreferredCategories,
    ProductViewTracker: publicWidget.registry.ProductViewTracker,
};
