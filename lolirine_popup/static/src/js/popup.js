/**
 * Lolirine Popup - JavaScript
 * Gère l'affichage, la fermeture et les cookies du popup
 * Supporte les popups standard et les popups de boxes disponibles
 * Supporte plusieurs modes d'affichage : all, shop, product, categories, pages, urls
 */

(function() {
    'use strict';

    // Attendre que le DOM soit prêt
    function initPopup() {
        var popup = document.getElementById('lolirine_popup_overlay');
        
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
        var popupType = popup.dataset.popupType || 'standard';
        
        // Config pour boxes disponibles
        var maxBoxes = parseInt(popup.dataset.maxBoxes) || 5;
        var boxesButtonText = popup.dataset.boxesButtonText || 'Réserver';
        var boxesContactUrl = popup.dataset.boxesContactUrl || '/contact-garde-meubles';
        var showPrice = popup.dataset.showPrice !== 'False';
        var showSize = popup.dataset.showSize !== 'False';

        console.log('[Lolirine Popup] Config:', {
            delay: delay,
            hideDuration: hideDuration,
            displayMode: displayMode,
            popupType: popupType,
            maxBoxes: maxBoxes,
            specificUrls: specificUrls,
            currentPath: window.location.pathname
        });

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
                    var isShop = currentPath.indexOf('/shop') !== -1 || 
                                 currentPath.indexOf('/product') !== -1 ||
                                 currentPath.indexOf('/category') !== -1;
                    return isShop;
                    
                case 'product':
                    // Pages produits uniquement (pas les catégories)
                    var isProduct = currentPath.indexOf('/shop/') !== -1 && 
                                    currentPath.indexOf('/category') === -1;
                    return isProduct;
                
                case 'categories':
                    // Catégories de produits spécifiques
                    if (specificUrls.length === 0) return false;
                    for (var i = 0; i < specificUrls.length; i++) {
                        var url = specificUrls[i].trim();
                        if (url && currentPath.indexOf(url) !== -1) {
                            return true;
                        }
                    }
                    return false;
                    
                case 'pages':
                    // Pages spécifiques sélectionnées
                    if (specificUrls.length === 0) return false;
                    for (var i = 0; i < specificUrls.length; i++) {
                        var url = specificUrls[i].trim();
                        // Match exact ou avec trailing slash
                        if (url && (currentPath === url || currentPath === url + '/')) {
                            return true;
                        }
                    }
                    return false;
                    
                case 'urls':
                    // URLs personnalisées (match partiel)
                    if (specificUrls.length === 0) return false;
                    for (var i = 0; i < specificUrls.length; i++) {
                        var url = specificUrls[i].trim();
                        if (url && currentPath.indexOf(url) !== -1) {
                            return true;
                        }
                    }
                    return false;
                    
                default:
                    return true;
            }
        }

        /**
         * Vérifie si le cookie existe
         */
        function hasClosedRecently() {
            var hasCookie = document.cookie.indexOf(cookieName + '=1') !== -1;
            return hasCookie;
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
         * Charge les boxes disponibles via API
         */
        function loadAvailableBoxes() {
            var loadingEl = popup.querySelector('.lolirine-boxes-loading');
            var listEl = popup.querySelector('.lolirine-boxes-list');
            var emptyEl = popup.querySelector('.lolirine-boxes-empty');
            
            if (!listEl) return;
            
            fetch('/lolirine-popup/available-boxes?limit=' + maxBoxes)
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    console.log('[Lolirine Popup] Boxes loaded:', data);
                    
                    if (loadingEl) loadingEl.style.display = 'none';
                    
                    if (data.success && data.boxes && data.boxes.length > 0) {
                        listEl.innerHTML = '';
                        
                        data.boxes.forEach(function(box) {
                            var boxEl = document.createElement('div');
                            boxEl.className = 'lolirine-box-item';
                            
                            var priceHtml = showPrice ? 
                                '<span class="lolirine-box-price">' + box.price.toFixed(2) + ' ' + box.currency + '/mois</span>' : '';
                            
                            var contactUrl = boxesContactUrl + '?box=' + encodeURIComponent(box.name) + '&box_id=' + box.id;
                            
                            boxEl.innerHTML = 
                                '<div class="lolirine-box-image">' +
                                    '<img src="' + box.image_url + '" alt="' + box.name + '" loading="lazy"/>' +
                                '</div>' +
                                '<div class="lolirine-box-info">' +
                                    '<h4 class="lolirine-box-name">' + box.name + '</h4>' +
                                    priceHtml +
                                '</div>' +
                                '<div class="lolirine-box-action">' +
                                    '<a href="' + contactUrl + '" class="btn lolirine-box-btn">' + boxesButtonText + '</a>' +
                                '</div>';
                            
                            listEl.appendChild(boxEl);
                            
                            // Track click
                            boxEl.querySelector('.lolirine-box-btn').addEventListener('click', function() {
                                trackClick();
                                setClosedCookie();
                            });
                        });
                        
                        listEl.style.display = 'block';
                        if (emptyEl) emptyEl.style.display = 'none';
                    } else {
                        // Aucun box disponible
                        listEl.style.display = 'none';
                        if (emptyEl) emptyEl.style.display = 'block';
                    }
                })
                .catch(function(error) {
                    console.error('[Lolirine Popup] Error loading boxes:', error);
                    if (loadingEl) loadingEl.style.display = 'none';
                    if (emptyEl) emptyEl.style.display = 'block';
                });
        }

        /**
         * Affiche le popup
         */
        function showPopup() {
            console.log('[Lolirine Popup] Showing popup!');
            
            // Si c'est un popup boxes, vérifier d'abord s'il y a des boxes disponibles
            if (popupType === 'available_boxes') {
                fetch('/lolirine-popup/available-boxes?limit=' + maxBoxes)
                    .then(function(response) { return response.json(); })
                    .then(function(data) {
                        if (data.success && data.boxes && data.boxes.length > 0) {
                            // Il y a des boxes disponibles, afficher le popup
                            popup.style.display = 'flex';
                            popup.offsetHeight;
                            popup.classList.add('show');
                            loadAvailableBoxes();
                            trackView();
                        } else {
                            console.log('[Lolirine Popup] No boxes available, not showing popup');
                        }
                    })
                    .catch(function(error) {
                        console.error('[Lolirine Popup] Error checking boxes:', error);
                    });
            } else {
                // Popup standard
                popup.style.display = 'flex';
                popup.offsetHeight;
                popup.classList.add('show');
                trackView();
            }
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
            console.log('[Lolirine Popup] Should not show on this page (mode:', displayMode, ')');
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

        // Track clics sur le bouton principal (popup standard)
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
        initPopup();
    }
    
    // Aussi initialiser après un court délai au cas où
    setTimeout(initPopup, 500);
})();
