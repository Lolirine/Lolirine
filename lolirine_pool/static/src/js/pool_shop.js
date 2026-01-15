/* ===========================================
   LOLIRINE POOL - JAVASCRIPT FRONTEND
   =========================================== */

document.addEventListener('DOMContentLoaded', function() {
    
    // Animation au scroll pour les catégories
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observer les cartes de catégorie
    document.querySelectorAll('.pool-category-card').forEach(function(card) {
        observer.observe(card);
    });

    // Filtre rapide par marque sur la page shop
    const brandFilter = document.querySelector('.pool-brand-filter');
    if (brandFilter) {
        brandFilter.addEventListener('change', function(e) {
            const brandId = e.target.value;
            if (brandId) {
                window.location.href = '/shop?brand=' + brandId;
            }
        });
    }

    // Smooth scroll pour les ancres
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                e.preventDefault();
                const target = document.querySelector(targetId);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Notification panier ajouté
    const addToCartButtons = document.querySelectorAll('.js_add_cart');
    addToCartButtons.forEach(function(btn) {
        btn.addEventListener('click', function() {
            // Animation du bouton
            this.classList.add('pool-btn-success');
            setTimeout(function() {
                btn.classList.remove('pool-btn-success');
            }, 1000);
        });
    });

    console.log('Lolirine Pool - Frontend loaded');
});
