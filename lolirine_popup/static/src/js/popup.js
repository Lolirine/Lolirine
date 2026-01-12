/**
 * Lolirine Popup - JavaScript
 * Gère l'affichage de plusieurs popups selon les pages configurées
 * Supporte les popups standard et les popups de boxes disponibles
 */

(function() {
    'use strict';

    // Attendre que le DOM soit prêt
    function initPopups() {
        // Trouver tous les popups sur la page
        var popups = document.querySelectorAll('[id^="lolirine_popup_overlay_"]');
        
        console.log('[Lolirine Popup] Found', popups.length, 'popups');
        
        if (popups.length === 0) {
            console.log('[Lolirine Popup] No popups found');
            return;
        }

        // Ne pas afficher en mode édition Odoo
        if (document.body.classList.contains('editor_enable') || 
            document.body.classList.contains('editor_has_snippets') ||
            document.querySelector('.o_edit_website_container')) {
            console.log('[Lolirine Popup] Edit mode detected, not showing');
            return;
        }

        // Trouver le popup approprié pour cette page
        var currentPath = window.location.pathname;
        var selectedPopup = null;
        var selectedDelay = 3000;
        
        for (var i = 0; i < popups.length; i++) {
            var popup = popups[i];
            if (shouldShowOnPage(popup, currentPath)) {
                if (!hasClosedRecently(popup)) {
                    selectedPopup = popup;
                    selectedDelay = parseInt(popup.dataset.delay) || 3000;
                    console.log('[Lolirine Popup] Selected popup:', popup.id, 'for path:', currentPath);
                    break; // Prendre le premier popup correspondant (par priorité)
                } else {
                    console.log('[Lolirine Popup] Popup', popup.id, 'already closed recently');
                }
            }
        }

        if (!selectedPopup) {
            console.log('[Lolirine Popup] No matching popup for this page');
            return;
        }

        // Initialiser le popup sélectionné
        initSinglePopup(selectedPopup, selectedDelay);
    }

    /**
     * Vérifie si le popup doit s'afficher sur cette page
     */
    function shouldShowOnPage(popup, currentPath) {
        var displayMode = popup.dataset.displayMode || 'all';
        var specificUrls = popup.dataset.specificUrls ? popup.dataset.specificUrls.split(',').filter(function(u) { return u.trim(); }) : [];
        
        console.log('[Lolirine Popup] Checking popup', popup.id, 'mode:', displayMode, 'urls:', specificUrls, 'path:', currentPath);
        
        switch (displayMode) {
            case 'all':
                return true;
                
            case 'shop':
                return currentPath.indexOf('/shop') !== -1 || 
                       currentPath.indexOf('/product') !== -1 ||
                       currentPath.indexOf('/category') !== -1;
                
            case 'product':
                return currentPath.indexOf('/shop/') !== -1 && 
                       currentPath.indexOf('/category') === -1;
            
            case 'categories':
            case 'pages':
            case 'urls':
                if (specificUrls.length === 0) return false;
                for (var i = 0; i < specificUrls.length; i++) {
                    var url = specificUrls[i].trim();
                    if (url) {
                        // Pour pages, match plus strict
                        if (displayMode === 'pages') {
                            if (currentPath === url || currentPath === url + '/') {
                                return true;
                            }
                        } else {
                            // Pour categories et urls, match partiel
                            if (currentPath.indexOf(url) !== -1) {
                                return true;
                            }
                        }
                    }
                }
                return false;
                
            default:
                return true;
        }
    }

    /**
     * Vérifie si le cookie existe pour ce popup
     */
    function hasClosedRecently(popup) {
        var popupId = popup.dataset.popupId || 'default';
        var cookieName = 'lolirine_popup_closed_' + popupId;
        return document.cookie.indexOf(cookieName + '=1') !== -1;
    }

    /**
     * Initialise un popup spécifique
     */
    function initSinglePopup(popup, delay) {
        var hideDuration = parseInt(popup.dataset.hideDuration) || 7;
        var popupId = popup.dataset.popupId || 'default';
        var popupType = popup.dataset.popupType || 'standard';
        var cookieName = 'lolirine_popup_closed_' + popupId;
        
        // Config pour boxes disponibles
        var maxBoxes = parseInt(popup.dataset.maxBoxes) || 5;
        var boxesButtonText = popup.dataset.boxesButtonText || 'Réserver';
        var boxesContactUrl = popup.dataset.boxesContactUrl || '/contact-garde-meubles';
        var showPrice = popup.dataset.showPrice !== 'False';

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
                            
                            boxEl.querySelector('.lolirine-box-btn').addEventListener('click', function() {
                                trackClick();
                                setClosedCookie();
                            });
                        });
                        
                        listEl.style.display = 'block';
                        if (emptyEl) emptyEl.style.display = 'none';
                    } else {
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
            console.log('[Lolirine Popup] Showing popup:', popup.id);
            
            if (popupType === 'available_boxes') {
                fetch('/lolirine-popup/available-boxes?limit=' + maxBoxes)
                    .then(function(response) { return response.json(); })
                    .then(function(data) {
                        if (data.success && data.boxes && data.boxes.length > 0) {
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
            console.log('[Lolirine Popup] Closing popup:', popup.id);
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

        // Afficher après le délai
        console.log('[Lolirine Popup] Will show popup', popup.id, 'in', delay, 'ms');
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
        document.addEventListener('DOMContentLoaded', initPopups);
    } else {
        initPopups();
    }
    
    // Aussi initialiser après un court délai au cas où
    setTimeout(initPopups, 500);
})();
