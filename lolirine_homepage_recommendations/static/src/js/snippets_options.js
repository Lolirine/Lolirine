/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

/**
 * Options pour les snippets de recommandation - Compatible Odoo 19
 */
options.registry.RecommendationsSection = options.Class.extend({
    
    /**
     * @override
     */
    start() {
        const result = this._super.apply(this, arguments);
        this._updateUIFromData();
        return result;
    },
    
    /**
     * Met à jour l'interface d'options depuis les data-attributes
     */
    _updateUIFromData() {
        const carousel = this.$target[0].querySelector('.recommendations-carousel');
        if (!carousel) return;
        
        // Synchroniser le type de section
        const sectionType = carousel.dataset.sectionType || 'best_sellers';
        this.$el.find('[data-select-data-attribute]').removeClass('active');
        this.$el.find(`[data-select-data-attribute="${sectionType}"]`).addClass('active');
    },
    
    /**
     * Appelé quand le type de section change
     */
    sectionType(previewMode, widgetValue, params) {
        const carousel = this.$target[0].querySelector('.recommendations-carousel');
        if (!carousel) return;
        
        carousel.dataset.sectionType = widgetValue;
        
        // Mettre à jour le titre et l'icône selon le type
        const configs = {
            'best_sellers': { title: 'Meilleures ventes', icon: 'fa-fire', color: 'text-primary' },
            'recently_viewed': { title: 'Produits récemment consultés', icon: 'fa-history', color: 'text-info' },
            'continue_shopping': { title: 'Continuez vos achats', icon: 'fa-shopping-cart', color: 'text-success' },
            'top_rated': { title: 'Les mieux notés', icon: 'fa-star', color: 'text-warning' },
            'promotions': { title: 'Offres du moment', icon: 'fa-tags', color: 'text-danger' },
            'new_arrivals': { title: 'Nouveautés', icon: 'fa-certificate', color: 'text-primary' },
            'related_to_viewed': { title: 'En lien avec vos consultations', icon: 'fa-link', color: 'text-secondary' },
            'for_category': { title: 'Pour vous dans cette catégorie', icon: 'fa-folder-open', color: 'text-primary' },
        };
        
        const config = configs[widgetValue] || configs['best_sellers'];
        
        const titleEl = this.$target[0].querySelector('.title-text');
        const iconEl = this.$target[0].querySelector('.recommendations-title i');
        
        if (titleEl) titleEl.textContent = config.title;
        if (iconEl) {
            iconEl.className = `fa ${config.icon} me-2 ${config.color}`;
        }
    },
    
    /**
     * Appelé quand le nombre de produits change
     */
    limit(previewMode, widgetValue, params) {
        const carousel = this.$target[0].querySelector('.recommendations-carousel');
        if (!carousel) return;
        
        carousel.dataset.limit = widgetValue || '12';
    },
    
    /**
     * Appelé quand l'option "masquer si vide" change
     */
    hideIfEmpty(previewMode, widgetValue, params) {
        const carousel = this.$target[0].querySelector('.recommendations-carousel');
        if (!carousel) return;
        
        carousel.dataset.hideIfEmpty = widgetValue ? 'true' : 'false';
    },
});

/**
 * Options pour la grille de catégories
 */
options.registry.PreferredCategoriesSection = options.Class.extend({
    
    /**
     * Appelé quand le nombre de catégories change
     */
    limit(previewMode, widgetValue, params) {
        const grid = this.$target[0].querySelector('.preferred-categories-grid');
        if (!grid) return;
        
        grid.dataset.limit = widgetValue || '6';
    },
});

export default {
    RecommendationsSection: options.registry.RecommendationsSection,
    PreferredCategoriesSection: options.registry.PreferredCategoriesSection,
};
