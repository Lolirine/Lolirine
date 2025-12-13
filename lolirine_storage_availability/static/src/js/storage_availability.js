/**
 * Lolirine Storage Availability
 * Remplace le bouton "Ajouter au panier" par "Contactez-nous" ou "Demande générale"
 */

(function () {
    'use strict';

    // Exécuter dès que possible
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Aussi exécuter après un court délai pour s'assurer que tout est chargé
    setTimeout(init, 500);
    setTimeout(init, 1500);

    var initialized = false;

    function init() {
        if (initialized) return;

        // Chercher les données injectées par le template QWeb
        var dataElement = document.getElementById('lolirine_storage_data');
        
        if (dataElement) {
            try {
                var data = JSON.parse(dataElement.textContent);
                if (data && data.is_storage_box) {
                    console.log('Lolirine Storage: Données trouvées dans le template', data);
                    initialized = true;
                    applyChanges(data);
                    return;
                }
            } catch (e) {
                console.error('Lolirine Storage: Erreur parsing JSON', e);
            }
        }

        // Fallback: appeler l'API si on est sur une page produit
        if (window.location.pathname.includes('/shop/')) {
            var slug = extractProductSlug();
            if (slug) {
                console.log('Lolirine Storage: Tentative API avec slug:', slug);
                fetchFromAPI(slug);
            }
        }
    }

    function extractProductSlug() {
        var path = window.location.pathname;
        var parts = path.split('/');
        
        for (var i = parts.length - 1; i >= 0; i--) {
            var part = parts[i];
            if (part && part.match(/-\d+$/)) {
                return part;
            }
        }
        return null;
    }

    function fetchFromAPI(slug) {
        fetch('/storage_box/get_data_by_slug/' + encodeURIComponent(slug))
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data && data.is_storage_box) {
                    console.log('Lolirine Storage: Données API reçues', data);
                    initialized = true;
                    applyChanges(data);
                }
            })
            .catch(function(e) {
                console.log('Lolirine Storage: Erreur API', e);
            });
    }

    function applyChanges(data) {
        console.log('Lolirine Storage: Application des changements...');
        
        // 1. MASQUER LE PANIER - très agressif
        hideCart();
        
        // 2. CRÉER LES BOUTONS
        var buttons = createButtons(data);
        
        // 3. INSÉRER LES BOUTONS
        insertButtons(buttons);

        // 4. Répéter le masquage après un délai (au cas où Odoo recharge des éléments)
        setTimeout(hideCart, 100);
        setTimeout(hideCart, 500);
        setTimeout(hideCart, 1000);
    }

    function hideCart() {
        // Liste exhaustive de tous les sélecteurs possibles pour le panier Odoo
        var selectorsToHide = [
            // Formulaires
            'form[action*="/shop/cart/update"]',
            'form[action*="cart"]',
            'form.js_add_cart_json',
            '#product_detail form',
            '.js_main_product form',
            
            // Boutons
            '#add_to_cart',
            'button[name="add_to_cart"]',
            '.js_check_product',
            '.o_wsale_product_btn',
            'a.a-submit',
            '.a-submit',
            'button.btn-primary[type="submit"]',
            
            // Quantité
            '.css_quantity',
            '.js_quantity',
            '.quantity',
            'input[name="add_qty"]',
            
            // Autres
            '.oe_product_cart',
            '.product_price + form',
            '.js_product > form',
            
            // Liste de souhaits et comparer (optionnel)
            // 'button[data-action="o_wishlist"]',
            // '.o_add_wishlist',
        ];

        var count = 0;
        selectorsToHide.forEach(function(selector) {
            document.querySelectorAll(selector).forEach(function(el) {
                if (el.style.display !== 'none') {
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('visibility', 'hidden', 'important');
                    el.style.setProperty('opacity', '0', 'important');
                    el.style.setProperty('height', '0', 'important');
                    el.style.setProperty('overflow', 'hidden', 'important');
                    count++;
                }
            });
        });

        // Ajouter classe au body
        document.body.classList.add('lolirine-storage-box');

        if (count > 0) {
            console.log('Lolirine Storage: ' + count + ' éléments panier masqués');
        }
    }

    function createButtons(data) {
        var container = document.createElement('div');
        container.id = 'lolirine_storage_buttons';
        container.className = 'lolirine-storage-buttons my-4';

        var html = '';

        // Badge de statut
        if (data.show_badge) {
            var badge = getBadgeInfo(data.storage_status, data.storage_status_display);
            html += '<div class="storage-status-badge mb-3 text-center">';
            html += '<span class="badge text-bg-' + badge.color + ' fs-5 px-4 py-2">';
            html += '<i class="fa ' + badge.icon + ' me-2"></i>' + badge.text;
            html += '</span></div>';
        }

        // Bouton RDV (disponible)
        if (data.show_appointment_button) {
            html += '<div class="storage-appointment-button mb-3">';
            html += '<a href="' + escapeHtml(data.appointment_url) + '" ';
            html += 'class="btn btn-primary btn-lg w-100 py-3" style="font-size:1.2rem;font-weight:bold;">';
            html += '<i class="fa fa-calendar me-2"></i>';
            html += escapeHtml(data.appointment_button_label);
            html += '</a>';
            html += '<p class="text-muted small mt-2 text-center mb-0">';
            html += '<i class="fa fa-info-circle me-1"></i> Prenez rendez-vous pour visiter ce box</p>';
            html += '</div>';
        }

        // Bouton Demande générale (non disponible)
        if (data.show_general_inquiry_button) {
            html += '<div class="storage-general-inquiry-button mb-3">';
            html += '<a href="' + escapeHtml(data.general_inquiry_url) + '" ';
            html += 'class="btn btn-secondary btn-lg w-100 py-3" style="font-size:1.2rem;font-weight:bold;">';
            html += '<i class="fa fa-envelope me-2"></i>';
            html += escapeHtml(data.general_inquiry_button_label);
            html += '</a>';
            html += '<p class="text-muted small mt-2 text-center mb-0">';
            html += '<i class="fa fa-info-circle me-1"></i> Ce box n\'est pas disponible actuellement</p>';
            html += '</div>';
        }

        container.innerHTML = html;
        return container;
    }

    function getBadgeInfo(status, displayText) {
        var badges = {
            'available': { color: 'success', icon: 'fa-check-circle', text: displayText || 'Disponible' },
            'rented': { color: 'danger', icon: 'fa-lock', text: displayText || 'Loué' },
            'reserved': { color: 'warning', icon: 'fa-clock-o', text: displayText || 'Réservé' },
            'maintenance': { color: 'secondary', icon: 'fa-wrench', text: displayText || 'En maintenance' }
        };
        return badges[status] || { color: 'secondary', icon: 'fa-question', text: displayText || 'Inconnu' };
    }

    function insertButtons(buttons) {
        // Vérifier si déjà inséré
        if (document.getElementById('lolirine_storage_buttons')) {
            console.log('Lolirine Storage: Boutons déjà présents');
            return;
        }

        // Essayer différents emplacements
        var targets = [
            // Priorité 1: Après le prix
            { sel: '.product_price', pos: 'after' },
            { sel: '[itemprop="offers"]', pos: 'after' },
            
            // Priorité 2: Remplacer le formulaire panier
            { sel: 'form[action*="/shop/cart/update"]', pos: 'before' },
            { sel: '#add_to_cart', pos: 'before' },
            
            // Priorité 3: Dans la section produit
            { sel: '.js_product', pos: 'append' },
            { sel: '#product_details', pos: 'append' },
            { sel: '#product_detail', pos: 'append' },
            
            // Fallback
            { sel: '.oe_website_sale', pos: 'append' }
        ];

        for (var i = 0; i < targets.length; i++) {
            var t = targets[i];
            var el = document.querySelector(t.sel);
            
            if (el) {
                if (t.pos === 'after' && el.parentNode) {
                    el.parentNode.insertBefore(buttons, el.nextSibling);
                } else if (t.pos === 'before' && el.parentNode) {
                    el.parentNode.insertBefore(buttons, el);
                } else if (t.pos === 'append') {
                    el.appendChild(buttons);
                }
                
                console.log('Lolirine Storage: Boutons insérés (' + t.sel + ' ' + t.pos + ')');
                return;
            }
        }

        console.warn('Lolirine Storage: Impossible de trouver un emplacement pour les boutons');
    }

    function escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

})();
