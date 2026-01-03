/**
 * Lolirine Storage Availability v3.9
 * - Boxes de stockage : remplace "Ajouter au panier" par "Voir les boxes disponibles" → /storage/plan
 * - Frais de dossier : remplace "Ajouter au panier" par "Voir les conditions" → /conditions-generales#table_of_content_heading_1_1
 * Compatible Odoo 18/19
 */

console.log('=== Lolirine Storage v3.9: Script chargé ===');

(function () {
    'use strict';

    var DONE = false;
    var currentUrl = window.location.pathname;

    // Exécuter seulement sur les pages /shop/
    if (currentUrl.includes('/shop/')) {
        
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

            // Vérifier si c'est le produit "Frais de dossier"
            if (slug.includes('frais-de-dossier') || slug.includes('frais-dossier')) {
                console.log('Lolirine Storage: Produit Frais de dossier détecté');
                DONE = true;
                transformFraisDossier();
                return;
            }
            
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

        function transformFraisDossier() {
            // Modifier le bouton "Ajouter au panier" pour Frais de dossier
            modifyCartButtonFraisDossier();
            hideQuantityControls();
            
            // Observer les changements
            var observer = new MutationObserver(function(mutations) {
                if (isEditorMode()) {
                    observer.disconnect();
                    return;
                }
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            if (node.id === 'add_to_cart' || 
                                (node.matches && node.matches('#add_to_cart, .js_check_product')) ||
                                (node.querySelector && node.querySelector('#add_to_cart, .js_check_product'))) {
                                setTimeout(function() {
                                    modifyCartButtonFraisDossier();
                                    hideQuantityControls();
                                }, 100);
                            }
                        }
                    });
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }

        function modifyCartButtonFraisDossier() {
            var cartButtons = document.querySelectorAll('#add_to_cart, button[name="add_to_cart"], .js_check_product');
            
            cartButtons.forEach(function(btn) {
                // Vérifier si déjà modifié
                if (btn.dataset.modified === 'true') return;
                
                // Créer un lien de remplacement
                var link = document.createElement('a');
                link.href = '/conditions-generales/#table_of_content_heading_1_1';
                link.className = btn.className;
                link.style.cssText = btn.style.cssText || '';
                link.innerHTML = '<i class="fa fa-info-circle me-2"></i>Voir les conditions';
                link.style.display = 'inline-flex';
                link.style.alignItems = 'center';
                link.style.justifyContent = 'center';
                link.style.textDecoration = 'none';
                link.dataset.modified = 'true';
                
                if (btn.parentNode) {
                    btn.parentNode.replaceChild(link, btn);
                    console.log('Lolirine Storage: Bouton Frais de dossier remplacé');
                }
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

            if (isEditorMode()) return;

            // 1. Ajouter les boutons personnalisés (badge + contact)
            createAndInsertButtons(data);

            // 2. Modifier le bouton "Ajouter au panier"
            modifyCartButton(data);

            // 3. Masquer les contrôles de quantité
            hideQuantityControls();

            // 4. Observer les changements pour re-appliquer si nécessaire
            observeChanges(data);
        }

        function modifyCartButton(data) {
            var cartButtons = document.querySelectorAll('#add_to_cart, button[name="add_to_cart"], .js_check_product');
            
            cartButtons.forEach(function(btn) {
                // Créer un lien de remplacement
                var link = document.createElement('a');
                link.href = '/storage/plan'; // URL vers le plan des boxes disponibles
                link.className = btn.className;
                link.style.cssText = btn.style.cssText || '';
                
                // Garder le même style mais changer le contenu
                link.innerHTML = '<i class="fa fa-search me-2"></i>Voir les boxes disponibles';
                
                // Ajouter des styles pour que ça ressemble au bouton original
                link.style.display = 'inline-flex';
                link.style.alignItems = 'center';
                link.style.justifyContent = 'center';
                link.style.textDecoration = 'none';
                
                // Remplacer le bouton par le lien
                if (btn.parentNode) {
                    btn.parentNode.replaceChild(link, btn);
                    console.log('Lolirine Storage: Bouton panier remplacé');
                }
            });
        }

        function hideQuantityControls() {
            // Masquer uniquement les contrôles de quantité
            var quantityControls = document.querySelectorAll('.css_quantity, .input-group.js_quantity');
            quantityControls.forEach(function(el) {
                el.style.setProperty('display', 'none', 'important');
            });
            console.log('Lolirine Storage: Contrôles de quantité masqués');
        }

        function observeChanges(data) {
            var observer = new MutationObserver(function(mutations) {
                if (isEditorMode()) {
                    observer.disconnect();
                    return;
                }
                
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            // Si un bouton panier est ajouté, le modifier
                            if (node.id === 'add_to_cart' || (node.matches && node.matches('#add_to_cart, .js_check_product'))) {
                                setTimeout(function() {
                                    modifyCartButton(data);
                                    hideQuantityControls();
                                }, 100);
                            }
                            // Vérifier aussi les enfants
                            if (node.querySelector && node.querySelector('#add_to_cart, .js_check_product')) {
                                setTimeout(function() {
                                    modifyCartButton(data);
                                    hideQuantityControls();
                                }, 100);
                            }
                        }
                    });
                });
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }

        function createAndInsertButtons(data) {
            if (isEditorMode()) return;

            var existing = document.getElementById('lolirine_storage_buttons');
            if (existing) existing.remove();

            var container = document.createElement('div');
            container.id = 'lolirine_storage_buttons';
            container.style.cssText = 'margin:20px 0;padding:20px;background:#f8f9fa;border-radius:12px;border:2px solid #e9ecef;';

            var html = '';

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

            var inserted = false;
            
            var priceEl = document.querySelector('.product_price, [itemprop="offers"], .oe_price');
            if (priceEl && priceEl.parentNode) {
                priceEl.parentNode.insertBefore(container, priceEl.nextSibling);
                inserted = true;
                console.log('Lolirine Storage: Boutons insérés après le prix');
            }

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

    } else {
        console.log('Lolirine Storage: Page hors /shop/, script ignoré');
    }

})();

})();
