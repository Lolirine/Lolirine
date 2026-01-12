/**
 * Lolirine Popup - JavaScript
 * Gère l'affichage, la fermeture et les cookies du popup
 */

(function() {
    'use strict';

    // Attendre que le DOM soit prêt
    function initPopup() {
        var popup = document.getElementById('lolirine_popup_overlay');
        
        // Debug
        console.log('[Lolirine Popup] Init - popup element:', popup);
        
        if (!popup) {
            console.log('[Lolirine Popup] No popup element found');
            return;
        }

        // Récupérer les paramètres depuis les attributs data
        var delay = parseInt(popup.dataset.delay) || 3000;
        var hideDuration = parseInt(popup.dataset.hideDuration) || 7;
        var displayMode = popup.dataset.displayMode || 'all';
        var specificUrls = popup.dataset.specificUrls ? popup.dataset.specificUrls.split(',').filter(function(u) { return u.trim(); }) : [];
        var popupId = popup.dataset.popupId || 'default';

        console.log('[Lolirine Popup] Config:', {
            delay: delay,
            hideDuration: hideDuration,
            displayMode: displayMode,
            specificUrls: specificUrls,
            popupId: popupId,
            currentPath: window.location.pathname
        });

        // Nom du cookie
        var cookieName = 'lolirine_popup_closed_' + popupId;

        /**
         * Vérifie si le popup doit s'afficher sur cette page
         */
        function shouldShowOnPage() {
            var currentPath = window.location.pathname;
            
            console.log('[Lolirine Popup] Checking display mode:', displayMode, 'for path:', currentPath);
            
            switch (displayMode) {
                case 'all':
                    return true;
                    
                case 'shop':
                    // Pages boutique : /shop, /shop/*, catégories, produits
                    var isShop = currentPath.indexOf('/shop') !== -1 || 
                                 currentPath.indexOf('/product') !== -1 ||
                                 currentPath.indexOf('/category') !== -1;
                    console.log('[Lolirine Popup] Is shop page:', isShop);
                    return isShop;
                    
                case 'product':
                    // Pages produits uniquement (contient /shop/ mais pas /category)
                    var isProduct = currentPath.indexOf('/shop/') !== -1 && 
                                    currentPath.indexOf('/category') === -1;
                    console.log('[Lolirine Popup] Is product page:', isProduct);
                    return isProduct;
                    
                case 'specific':
                    // URLs spécifiques
                    for (var i = 0; i < specificUrls.length; i++) {
                        var url = specificUrls[i].trim();
                        if (url && currentPath.indexOf(url) !== -1) {
                            console.log('[Lolirine Popup] Matched specific URL:', url);
                            return true;
                        }
                    }
                    console.log('[Lolirine Popup] No specific URL matched');
                    return false;
                    
                default:
                    return true;
            }
        }

        /**
         * Vérifie si le cookie existe (popup déjà fermé récemment)
         */
        function hasClosedRecently() {
            var hasCookie = document.cookie.indexOf(cookieName + '=1') !== -1;
            console.log('[Lolirine Popup] Has closed cookie:', hasCookie);
            return hasCookie;
        }

        /**
         * Définit le cookie pour masquer le popup
         */
        function setClosedCookie() {
            var date = new Date();
            date.setTime(date.getTime() + (hideDuration * 24 * 60 * 60 * 1000));
            document.cookie = cookieName + '=1; expires=' + date.toUTCString() + '; path=/; SameSite=Lax';
            console.log('[Lolirine Popup] Cookie set for', hideDuration, 'days');
        }

        /**
         * Affiche le popup
         */
        function showPopup() {
            console.log('[Lolirine Popup] Showing popup!');
            popup.style.display = 'flex';
            // Forcer le reflow pour l'animation
            popup.offsetHeight;
            popup.classList.add('show');
            
            // Incrémenter le compteur de vues
            trackView();
        }

        /**
         * Ferme le popup
         */
        function closePopup() {
            console.log('[Lolirine Popup] Closing popup');
            popup.classList.remove('show');
            setTimeout(function() {
                popup.style.display = 'none';
            }, 300);
            setClosedCookie();
        }

        /**
         * Track les vues
         */
        function trackView() {
            fetch('/lolirine-popup/track-view/' + popupId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).catch(function(e) {
                console.log('[Lolirine Popup] Track view error:', e);
            });
        }

        /**
         * Track les clics
         */
        function trackClick() {
            fetch('/lolirine-popup/track-click/' + popupId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).catch(function(e) {
                console.log('[Lolirine Popup] Track click error:', e);
            });
        }

        // Ne pas afficher en mode édition Odoo
        if (document.body.classList.contains('editor_enable') || 
            document.body.classList.contains('editor_has_snippets') ||
            document.querySelector('.o_edit_website_container')) {
            console.log('[Lolirine Popup] Edit mode detected, not showing');
            return;
        }

        // Vérifier les conditions d'affichage
        if (!shouldShowOnPage()) {
            console.log('[Lolirine Popup] Should not show on this page');
            return;
        }

        if (hasClosedRecently()) {
            console.log('[Lolirine Popup] Already closed recently');
            return;
        }

        // Afficher après le délai
        console.log('[Lolirine Popup] Will show in', delay, 'ms');
        setTimeout(showPopup, delay);

        // Gestionnaire de fermeture - bouton X
        var closeBtn = popup.querySelector('.lolirine-popup-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                closePopup();
            });
        }

        // Gestionnaire de fermeture - clic sur l'overlay
        popup.addEventListener('click', function(e) {
            if (e.target === popup) {
                closePopup();
            }
        });

        // Gestionnaire de fermeture - touche Escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && popup.classList.contains('show')) {
                closePopup();
            }
        });

        // Track clics sur le bouton principal
        var primaryBtn = popup.querySelector('.lolirine-popup-btn-primary');
        if (primaryBtn) {
            primaryBtn.addEventListener('click', function() {
                trackClick();
                setClosedCookie();
            });
        }
    }

    // Initialiser quand le DOM est prêt
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPopup);
    } else {
        // DOM déjà chargé
        initPopup();
    }
    
    // Aussi initialiser après un court délai au cas où
    setTimeout(initPopup, 500);
})();

