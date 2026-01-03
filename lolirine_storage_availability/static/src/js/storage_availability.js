/**
 * Lolirine Storage Availability v3.6 - VERSION TEST SANS MASQUAGE
 * Cette version n'effectue AUCUN masquage pour identifier la source du problème
 */

console.log('=== Lolirine Storage v3.6 TEST: Script chargé (SANS MASQUAGE) ===');

(function () {
    'use strict';

    var DONE = false;

    // Démarrer seulement sur les pages /shop/
    var currentUrl = window.location.pathname;
    if (!currentUrl.includes('/shop/')) {
        console.log('Lolirine Storage: Pas sur /shop/, script ignoré');
        return;
    }

    init();
    document.addEventListener('DOMContentLoaded', init);
    window.addEventListener('load', init);
    setTimeout(init, 1000);
    setTimeout(init, 2000);

    function isEditorMode() {
        return document.body.classList.contains('editor_enable') || 
               document.body.classList.contains('o_edit_mode') ||
               document.querySelector('.o_we_website_top_actions') ||
               document.querySelector('#oe_snippets') ||
               document.querySelector('.o_website_preview') ||
               window.location.href.includes('enable_editor') ||
               window.location.href.includes('edit_translations') ||
               document.body.dataset.edit === '1' ||
               document.body.dataset.edit === 'true';
    }

    function init() {
        if (DONE) return;

        if (isEditorMode()) {
            console.log('Lolirine Storage: Mode édition détecté, script désactivé');
            return;
        }

        var slug = getSlug(window.location.pathname);
        if (!slug) return;

        console.log('Lolirine Storage: Slug = ' + slug);
        
        fetch('/storage_box/get_data_by_slug/' + encodeURIComponent(slug))
            .then(function(r) { return r.json(); })
            .then(function(data) {
                console.log('Lolirine Storage: Data = ', data);
                if (data && data.is_storage_box) {
                    DONE = true;
                    // UNIQUEMENT ajouter les boutons, SANS masquer quoi que ce soit
                    createAndInsertButtons(data);
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

    function createAndInsertButtons(data) {
        if (isEditorMode()) return;

        // Supprimer si déjà présent
        var existing = document.getElementById('lolirine_storage_buttons');
        if (existing) existing.remove();

        // Créer le conteneur
        var container = document.createElement('div');
        container.id = 'lolirine_storage_buttons';
        container.style.cssText = 'margin:20px 0;padding:20px;background:#f8f9fa;border-radius:12px;border:2px solid #e9ecef;';

        var html = '';

        // Badge de statut
        if (data.show_badge !== false) {
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
            html += '<a href="' + escHtml(data.appointment_url || '/appointment') + '" ';
            html += 'style="display:block;width:100%;padding:18px;font-size:20px;font-weight:bold;text-align:center;color:#fff;background:#007bff;border:none;border-radius:10px;text-decoration:none;box-shadow:0 4px 6px rgba(0,0,0,0.1);">';
            html += '<i class="fa fa-calendar" style="margin-right:10px;"></i>';
            html += escHtml(data.appointment_button_label || 'Contactez-nous');
            html += '</a>';
            html += '<p style="text-align:center;color:#666;margin-top:10px;margin-bottom:0;font-size:14px;">';
            html += '<i class="fa fa-info-circle"></i> Prenez rendez-vous pour visiter ce box</p>';
        } else if (data.storage_status !== 'available') {
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

        // Sinon, essayer dans la zone produit
        if (!inserted) {
            var productDetail = document.querySelector('#product_details, #product_detail, .js_product');
            if (productDetail) {
                productDetail.appendChild(container);
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

})();
