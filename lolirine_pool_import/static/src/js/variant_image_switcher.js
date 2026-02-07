/** @odoo-module */
/**
 * Pool Variant Image Switcher
 * ===========================
 * Écoute les changements de sélection d'attributs sur la page produit
 * et remplace l'image principale par l'image de la PTAV sélectionnée.
 *
 * Fonctionne avec :
 *   - Radio buttons (standard Odoo)
 *   - Color pickers (Couleur Cuve)
 *   - Select dropdowns
 *   - Boutons visuels personnalisés
 *
 * Architecture :
 *   1. Au chargement, appel JSON → /pool/variant_images/<tmpl_id>
 *   2. Stocke le mapping ptav_id → image_url
 *   3. Sur chaque changement d'attribut, cherche si une image existe
 *   4. Si oui, swap le src de l'image principale avec transition fade
 */

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PoolVariantImageSwitcher = publicWidget.Widget.extend({
    selector: '#product_detail, .oe_website_sale .o_wsale_product_page',
    events: {
        'change .js_variant_change, .variant_attribute_value': '_onVariantChange',
        'click .css_attribute_color input': '_onVariantChange',
        'click input[type="radio"].js_variant_change': '_onVariantChange',
        'click .o_variant_pills .btn': '_onVariantChange',
    },

    /**
     * @override
     */
    start() {
        this._super(...arguments);
        this.variantImageData = {};
        this.defaultImageUrl = '';
        this._originalImageSrc = '';
        this._loadVariantImages();
    },

    // ─── Chargement des données ───────────────────────────────────

    async _loadVariantImages() {
        // Trouver le product.template ID
        const productEl = this.el.querySelector(
            'input[name="product_template_id"], '
            + '.product_template_id, '
            + '[data-product-template-id]'
        );

        let tmplId = 0;

        if (productEl) {
            tmplId = parseInt(
                productEl.value
                || productEl.dataset.productTemplateId
                || productEl.textContent
            , 10);
        }

        // Fallback : chercher dans le formulaire add-to-cart
        if (!tmplId) {
            const form = this.el.querySelector('form[action*="/shop/cart/update"]');
            if (form) {
                const hiddenField = form.querySelector('input[name="product_id"]');
                if (hiddenField) {
                    // product_id est un product.product, on doit chercher le template
                    // Le template_id est souvent dans un autre champ
                    const tmplField = form.querySelector(
                        'input[name="product_template_id"]'
                    );
                    if (tmplField) {
                        tmplId = parseInt(tmplField.value, 10);
                    }
                }
            }
        }

        // Encore un fallback : data attribute sur le body ou la page
        if (!tmplId) {
            const bodyData = document.body.dataset.productTemplateId;
            if (bodyData) tmplId = parseInt(bodyData, 10);
        }

        if (!tmplId) {
            return;  // Pas sur une page produit
        }

        // Stocker l'image originale
        const mainImg = this._getMainImage();
        if (mainImg) {
            this._originalImageSrc = mainImg.src;
        }

        // Charger les images variantes via JSON-RPC
        try {
            const result = await this._rpc({
                route: `/pool/variant_images/${tmplId}`,
                params: {},
            });

            if (result && result.attribute_values) {
                this.variantImageData = result.attribute_values;
                this.defaultImageUrl = result.default_image_url || '';
                this._enhanceAttributeSelectors();
            }
        } catch (e) {
            // Silencieux : le produit n'a peut-être pas d'images variantes
            console.debug('Pool variant images: pas de données', e);
        }
    },

    // ─── Event handler ────────────────────────────────────────────

    _onVariantChange(ev) {
        // Petit délai pour laisser Odoo traiter son propre changement
        setTimeout(() => this._updateImage(), 50);
    },

    _updateImage() {
        if (!Object.keys(this.variantImageData).length) return;

        // Lire toutes les valeurs d'attribut sélectionnées
        const selectedPtavIds = this._getSelectedPtavIds();
        let imageUrl = '';

        // Chercher la première PTAV sélectionnée qui a une image
        // Priorité aux attributs visuels (Couleur, Meuble)
        const priorityAttrs = ['couleur', 'meuble', 'color', 'finition'];

        // D'abord les attributs prioritaires
        for (const ptavId of selectedPtavIds) {
            const data = this.variantImageData[String(ptavId)];
            if (data && data.has_image) {
                const attrLower = (data.attribute_name || '').toLowerCase();
                if (priorityAttrs.some(p => attrLower.includes(p))) {
                    imageUrl = data.image_url || data.image_url_external;
                    break;
                }
            }
        }

        // Si aucun attribut prioritaire, prendre le premier avec image
        if (!imageUrl) {
            for (const ptavId of selectedPtavIds) {
                const data = this.variantImageData[String(ptavId)];
                if (data && data.has_image) {
                    imageUrl = data.image_url || data.image_url_external;
                    break;
                }
            }
        }

        // Appliquer l'image
        if (imageUrl) {
            this._swapMainImage(imageUrl);
        } else if (this._originalImageSrc) {
            // Revenir à l'image par défaut
            this._swapMainImage(this._originalImageSrc);
        }
    },

    // ─── Manipulation DOM ─────────────────────────────────────────

    _getMainImage() {
        // Odoo 17+ : image dans le carrousel produit
        return (
            this.el.querySelector('.o_wsale_product_images img.product_detail_img')
            || this.el.querySelector('#o-carousel-product .carousel-item.active img')
            || this.el.querySelector('.product_detail_img')
            || this.el.querySelector('.o_wsale_product_main_image img')
            || this.el.querySelector('.oe_product_image img')
        );
    },

    _swapMainImage(newUrl) {
        const img = this._getMainImage();
        if (!img || img.src === newUrl) return;

        // Transition fade
        img.style.transition = 'opacity 0.25s ease';
        img.style.opacity = '0.3';

        // Précharger la nouvelle image
        const preloader = new Image();
        preloader.onload = () => {
            img.src = newUrl;
            img.style.opacity = '1';
        };
        preloader.onerror = () => {
            img.style.opacity = '1';  // Restaurer même si erreur
        };
        preloader.src = newUrl;

        // Mettre à jour aussi le zoom (loupe) si présent
        const zoomTarget = this.el.querySelector('[data-zoom-image]');
        if (zoomTarget) {
            zoomTarget.dataset.zoomImage = newUrl;
        }

        // Mettre à jour l'attribut data-src pour lazy loading
        if (img.dataset.src) {
            img.dataset.src = newUrl;
        }
    },

    _getSelectedPtavIds() {
        const ids = [];
        // Radio buttons
        this.el.querySelectorAll(
            'input.js_variant_change:checked, '
            + '.variant_attribute_value:checked, '
            + 'input[type="radio"].js_variant_change:checked'
        ).forEach(input => {
            const val = parseInt(input.value || input.dataset.value_id || 0, 10);
            // Le value est souvent le product.template.attribute.value ID
            if (val) ids.push(val);
        });

        // Select dropdowns
        this.el.querySelectorAll('select.js_variant_change').forEach(select => {
            const val = parseInt(select.value, 10);
            if (val) ids.push(val);
        });

        // Color pickers (active)
        this.el.querySelectorAll('.css_attribute_color input:checked').forEach(input => {
            const val = parseInt(input.value || input.dataset.value_id || 0, 10);
            if (val) ids.push(val);
        });

        // Pills (boutons actifs)
        this.el.querySelectorAll('.o_variant_pills .btn.active').forEach(btn => {
            const val = parseInt(
                btn.dataset.value_id || btn.dataset.attributeValueId || 0
            , 10);
            if (val) ids.push(val);
        });

        return ids;
    },

    // ─── Enhancement : miniatures sur les sélecteurs ──────────────

    _enhanceAttributeSelectors() {
        /**
         * Ajoute des miniatures d'image aux sélecteurs d'attributs
         * quand la PTAV a une image (radio buttons → petite vignette).
         */
        for (const [ptavId, data] of Object.entries(this.variantImageData)) {
            if (!data.has_image) continue;

            // Trouver le sélecteur correspondant
            const selector = this.el.querySelector(
                `input[value="${ptavId}"], `
                + `[data-value_id="${ptavId}"], `
                + `[data-attribute-value-id="${ptavId}"]`
            );

            if (!selector) continue;

            // Ajouter une miniature à côté du label
            const label = selector.closest('label')
                || selector.parentElement.querySelector('label')
                || selector.nextElementSibling;

            if (label && !label.querySelector('.pool-variant-thumb')) {
                const thumb = document.createElement('img');
                thumb.classList.add('pool-variant-thumb');
                thumb.src = `/pool/variant_image_128/${ptavId}`;
                thumb.alt = data.value_name;
                thumb.style.cssText = [
                    'width: 32px',
                    'height: 32px',
                    'object-fit: cover',
                    'border-radius: 4px',
                    'margin-right: 6px',
                    'vertical-align: middle',
                    'border: 1px solid #ddd',
                ].join('; ');
                label.insertBefore(thumb, label.firstChild);
            }
        }
    },

    /**
     * Compatibility: Odoo 19 _rpc wrapper
     */
    async _rpc(params) {
        // Try the OWL rpc service first, fallback to legacy
        if (this.rpc) {
            return this.rpc(params.route, params.params || {});
        }
        // Legacy jQuery approach
        return $.ajax({
            url: params.route,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: params.params || {},
            }),
        }).then(response => response.result);
    },
});

export default publicWidget.registry.PoolVariantImageSwitcher;
