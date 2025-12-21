/**
 * Lolirine Storage Availability v3
 * Remplace le bouton "Ajouter au panier" par "Contactez-nous" ou "Demande générale"
 * Compatible Odoo 18
 */

console.log('=== Lolirine Storage v3: Script chargé ===');

(function () {
    'use strict';

    var DONE = false;

    // Démarrer
    init();
    document.addEventListener('DOMContentLoaded', init);
    window.addEventListener('load', init);
    setTimeout(init, 1000);
    setTimeout(init, 2000);

    function init() {
        if (DONE) return;

        var url = window.location.pathname;
        if (!url.includes('/shop/')) return;

        var slug = getSlug(url);
        if (!slug) return;

        console.log('Lolirine Storage: Slug = ' + slug);
        
        fetch('/storage_box/get_data_by_slug/' + encodeURIComponent(slug))
            .then(function(r) { return r.json(); })
            .then(function(data) {
                console.log('Lolirine Storage: Data = ', data);
                if (data && data.is_storage_box) {
                    DONE = true;
                    transform(data);
                }
            })
            .catch(function(e) {
                console.error('Lolirine Storage: Erreur', e);
            });
    }

    function getSlug(url) {
        var parts = url.split('/');
        for (var i = parts.length - 1; i >= 0; i--) {
            if (parts[i] && parts[i].match(/-\d+$/)) {
                return parts[i];
            }
        }
        return null;
    }

    function transform(data) {
        console.log('Lolirine Storage: === TRANSFORMATION ===');

        // 1. MASQUER TOUT LE PANIER - très agressif
        hideAllCartElements();

        // 2. CRÉER ET INSÉRER LES BOUTONS
        createAndInsertButtons(data);

        // 3. RÉPÉTER LE MASQUAGE
        setInterval(hideAllCartElements, 500);
    }

    function hideAllCartElements() {
        // Liste complète de tous les sélecteurs possibles pour Odoo 18
        var hide = [
            // Formulaires
            'form[action*="cart"]',
            'form.js_add_cart_json',
            'form.o_wsale_product_page_form',
            '#product_detail form',
            '.js_main_product form',
            
            // Boutons ajouter au panier
            '#add_to_cart',
            'button#add_to_cart',
            'a#add_to_cart',
            '[name="add_to_cart"]',
            '.js_check_product',
            '.a-submit',
            'a.a-submit',
            '.o_wsale_product_btn',
            '.btn-primary[type="submit"]',
            
            // Quantité
            '.css_quantity',
            '.js_quantity',
            '.quantity',
            'input[name="add_qty"]',
            '.input-group.js_quantity',
            
            // Autres éléments e-commerce
            '.oe_product_cart',
            '.o_product_page_add_to_cart',
            '.product_price + form',
            
            // Wishlist et compare (garder si besoin, commenter sinon)
            // '.o_add_wishlist_dyn',
            // '.o_add_compare_dyn',
        ];

        var count = 0;
        hide.forEach(function(sel) {
            document.querySelectorAll(sel).forEach(function(el) {
                // Ne pas masquer nos propres boutons
                if (el.closest('#lolirine_storage_buttons')) return;
                if (el.id === 'lolirine_storage_buttons') return;
                
                if (el.style.display !== 'none') {
                    el.style.cssText = 'display:none!important;visibility:hidden!important;opacity:0!important;height:0!important;overflow:hidden!important;position:absolute!important;left:-9999px!important;';
                    count++;
                }
            });
        });

        // Masquer aussi par classe
        document.body.classList.add('lolirine-storage-box');

        if (count > 0) {
            console.log('Lolirine Storage: ' + count + ' éléments masqués');
        }
    }

    function createAndInsertButtons(data) {
        // Supprimer si déjà présent
        var existing = document.getElementById('lolirine_storage_buttons');
        if (existing) existing.remove();

        // Créer le conteneur
        var container = document.createElement('div');
        container.id = 'lolirine_storage_buttons';
        container.style.cssText = 'margin:20px 0;padding:20px;background:#f8f9fa;border-radius:12px;border:2px solid #e9ecef;';

        var html = '';

        // Badge de statut
        if (data.show_badge !== false) {  // Afficher par défaut
            var badge = {
                'available': { bg: '#28a745', icon: 'fa-check-circle', text: data.storage_status_display || 'Disponible' },
                'rented': { bg: '#dc3545', icon: 'fa-lock', text: data.storage_status_display || 'Loué' },
                'reserved': { bg: '#ffc107', icon: 'fa-clock-o', text: data.storage_status_display || 'Réservé' },
                'maintenance': { bg: '#6c757d', icon: 'fa-wrench', text: data.storage_status_display || 'En maintenance' }
            }[data.storage_status] || { bg: '#6c757d', icon: 'fa-question', text: 'Inconnu' };

            html += '<div style="text-align:center;margin-bottom:15px;">';
            html += '<span style="display:inline-block;padding:10px 25px;font-size:18px;font-weight:bold;color:#fff;background:' + badge.bg + ';border-radius:25px;">';
            html += '<i class="fa ' + badge.icon + '" style="margin-right:10px;"></i>' + escHtml(badge.text);
            html += '</span></div>';
        }

        // Bouton selon le statut
        if (data.storage_status === 'available' && data.show_appointment_button) {
            // Box DISPONIBLE -> Bouton RDV
            html += '<a href="' + escHtml(data.appointment_url || '/appointment') + '" ';
            html += 'style="display:block;width:100%;padding:18px;font-size:20px;font-weight:bold;text-align:center;color:#fff;background:#007bff;border:none;border-radius:10px;text-decoration:none;box-shadow:0 4px 6px rgba(0,0,0,0.1);">';
            html += '<i class="fa fa-calendar" style="margin-right:10px;"></i>';
            html += escHtml(data.appointment_button_label || 'Contactez-nous');
            html += '</a>';
            html += '<p style="text-align:center;color:#666;margin-top:10px;margin-bottom:0;font-size:14px;">';
            html += '<i class="fa fa-info-circle"></i> Prenez rendez-vous pour visiter ce box</p>';
        } else if (data.storage_status !== 'available') {
            // Box NON DISPONIBLE -> Bouton demande générale
            html += '<a href="' + escHtml(data.general_inquiry_url || '/contactus') + '" ';
            html += 'style="display:block;width:100%;padding:18px;font-size:20px;font-weight:bold;text-align:center;color:#fff;background:#6c757d;border:none;border-radius:10px;text-decoration:none;box-shadow:0 4px 6px rgba(0,0,0,0.1);">';
            html += '<i class="fa fa-envelope" style="margin-right:10px;"></i>';
            html += escHtml(data.general_inquiry_button_label || 'Demande générale');
            html += '</a>';
            html += '<p style="text-align:center;color:#666;margin-top:10px;margin-bottom:0;font-size:14px;">';
            html += '<i class="fa fa-info-circle"></i> Ce box n\'est pas disponible actuellement</p>';
        }

        container.innerHTML = html;

        // INSERTION - trouver le meilleur endroit
        var inserted = false;
        
        // Essayer après le prix
        var priceEl = document.querySelector('.product_price, [itemprop="offers"], .oe_price');
        if (priceEl && priceEl.parentNode) {
            priceEl.parentNode.insertBefore(container, priceEl.nextSibling);
            inserted = true;
            console.log('Lolirine Storage: Boutons insérés après le prix');
        }

        // Sinon, essayer avant le formulaire panier
        if (!inserted) {
            var formEl = document.querySelector('form[action*="cart"], #add_to_cart, .js_check_product');
            if (formEl && formEl.parentNode) {
                formEl.parentNode.insertBefore(container, formEl);
                inserted = true;
                console.log('Lolirine Storage: Boutons insérés avant le formulaire');
            }
        }

        // Sinon, ajouter dans product_detail
        if (!inserted) {
            var detailEl = document.querySelector('#product_details, #product_detail, .js_product');
            if (detailEl) {
                detailEl.appendChild(container);
                inserted = true;
                console.log('Lolirine Storage: Boutons ajoutés dans product_detail');
            }
        }

        if (!inserted) {
            console.warn('Lolirine Storage: IMPOSSIBLE d\'insérer les boutons!');
        }
    }

    function escHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

})();
