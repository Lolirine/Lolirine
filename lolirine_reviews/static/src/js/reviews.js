/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.LolirineReviews = publicWidget.Widget.extend({
    selector: '.s_lolirine_reviews',
    
    start: function () {
        this._super.apply(this, arguments);
        this._initCarousel();
        return Promise.resolve();
    },
    
    _initCarousel: function () {
        const carousel = this.el.querySelector('.lr-carousel');
        const dotsContainer = this.el.querySelector('.lr-pagination');
        const prevBtn = this.el.querySelector('.lr-nav-prev');
        const nextBtn = this.el.querySelector('.lr-nav-next');
        
        if (!carousel) return;
        
        const cards = carousel.querySelectorAll('.lr-card');
        const cardWidth = 364; // card width + gap
        const visibleCards = Math.max(1, Math.floor(carousel.offsetWidth / cardWidth));
        const totalDots = Math.ceil(cards.length / visibleCards);
        
        // Créer les dots de pagination
        if (dotsContainer) {
            dotsContainer.innerHTML = '';
            for (let i = 0; i < Math.min(totalDots, 8); i++) {
                const dot = document.createElement('button');
                dot.className = 'lr-dot' + (i === 0 ? ' active' : '');
                dot.type = 'button';
                dot.addEventListener('click', () => this._scrollToPage(carousel, i, cardWidth, visibleCards));
                dotsContainer.appendChild(dot);
            }
        }
        
        // Navigation précédent
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                carousel.scrollBy({ left: -cardWidth * 2, behavior: 'smooth' });
            });
        }
        
        // Navigation suivant
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                carousel.scrollBy({ left: cardWidth * 2, behavior: 'smooth' });
            });
        }
        
        // Mise à jour des dots au scroll
        carousel.addEventListener('scroll', () => {
            const scrollPosition = carousel.scrollLeft;
            const currentPage = Math.round(scrollPosition / (cardWidth * visibleCards));
            const dots = dotsContainer ? dotsContainer.querySelectorAll('.lr-dot') : [];
            dots.forEach((dot, i) => {
                dot.classList.toggle('active', i === currentPage);
            });
        });
    },
    
    _scrollToPage: function (carousel, page, cardWidth, visibleCards) {
        carousel.scrollTo({ left: page * cardWidth * visibleCards, behavior: 'smooth' });
    },
});

export default publicWidget.registry.LolirineReviews;
