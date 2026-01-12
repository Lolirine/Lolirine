/**
 * Lolirine Popup - JavaScript
 * Gère l'affichage, la fermeture et les cookies du popup
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        var popup = document.getElementById('lolirine_popup_overlay');
        if (!popup) return;

        // Récupérer les paramètres depuis les attributs data
        var delay = parseInt(popup.dataset.delay) || 3000;
        var hideDuration = parseInt(popup.dataset.hideDuration) || 7;
        var displayMode = popup.dataset.displayMode || 'all';
        var specificUrls = popup.dataset.specificUrls ? popup.dataset.specificUrls.split(',') : [];
        var popupId = popup.dataset.popupId || 'default';

        // Nom du cookie
        var cookieName = 'lolirine_popup_closed_' + popupId;

        /**
         * Vérifie si le popup doit s'afficher sur cette page
         */
        function shouldShowOnPage() {
            var currentPath = window.location.pathname;
            
            switch (displayMode) {
                case 'all':
                    return true;
                    
                case 'shop':
                    // Pages boutique : /shop, /shop/*, catégories, produits
                    return currentPath.indexOf('/shop') === 0 || 
                           currentPath.indexOf('/product') === 0;
                    
                case 'product':
                    // Pages produits uniquement
                    return currentPath.indexOf('/shop/') === 0 && 
                           currentPath.indexOf('/category') === -1;
                    
                case 'specific':
                    // URLs spécifiques
                    for (var i = 0; i < specificUrls.length; i++) {
                        var url = specificUrls[i].trim();
                        if (url && currentPath.indexOf(url) === 0) {
                            return true;
                        }
                    }
                    return false;
                    
                default:
                    return true;
            }
        }

        /**
         * Vérifie si le cookie existe (popup déjà fermé récemment)
         */
        function hasClosedRecently() {
            return document.cookie.indexOf(cookieName + '=1') !== -1;
        }

        /**
         * Définit le cookie pour masquer le popup
         */
        function setClosedCookie() {
            var date = new Date();
            date.setTime(date.getTime() + (hideDuration * 24 * 60 * 60 * 1000));
            document.cookie = cookieName + '=1; expires=' + date.toUTCString() + '; path=/; SameSite=Lax';
        }

        /**
         * Affiche le popup
         */
        function showPopup() {
            popup.style.display = 'flex';
            // Forcer le reflow pour l'animation
            popup.offsetHeight;
            popup.classList.add('show');
            
            // Incrémenter le compteur de vues (optionnel - via AJAX)
            trackView();
        }

        /**
         * Ferme le popup
         */
        function closePopup() {
            popup.classList.remove('show');
            setTimeout(function() {
                popup.style.display = 'none';
            }, 300);
            setClosedCookie();
        }

        /**
         * Track les vues (optionnel)
         */
        function trackView() {
            // Appel AJAX pour incrémenter le compteur
            fetch('/lolirine-popup/track-view/' + popupId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            }).catch(function() {
                // Ignorer les erreurs de tracking
            });
        }

        /**
         * Track les clics (optionnel)
         */
        function trackClick() {
            fetch('/lolirine-popup/track-click/' + popupId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            }).catch(function() {
                // Ignorer les erreurs
            });
        }

        // Vérifier les conditions d'affichage
        if (!shouldShowOnPage()) {
            return;
        }

        if (hasClosedRecently()) {
            return;
        }

        // Ne pas afficher en mode édition
        if (document.body.classList.contains('editor_enable') || 
            document.body.classList.contains('editor_has_snippets')) {
            return;
        }

        // Afficher après le délai
        setTimeout(showPopup, delay);

        // Gestionnaire de fermeture - bouton X
        var closeBtn = popup.querySelector('.lolirine-popup-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function(e) {
                e.preventDefault();
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
                setClosedCookie(); // Fermer aussi après clic
            });
        }
    });
})();
