/**
 * Lolirine Storage Availability
 * Script pour remplacer le bouton panier par les boutons RDV/Contact
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        // Chercher les données du box de stockage dans la page
        var dataElement = document.getElementById('storage_box_data');
        if (!dataElement) return;

        var data;
        try {
            data = JSON.parse(dataElement.textContent);
        } catch (e) {
            console.error('Lolirine Storage: Error parsing storage data', e);
            return;
        }

        if (!data || !data.is_storage_box) return;

        console.log('Lolirine Storage: Box de stockage détecté', data);

        // 1. Masquer le formulaire panier et les éléments associés
        hideCartElements();

        // 2. Créer le conteneur pour les boutons
        var container = createButtonsContainer(data);

        // 3. Insérer le conteneur après le prix ou à la place du formulaire panier
        insertContainer(container);
    });

    /**
     * Masque tous les éléments du panier
     */
    function hideCartElements() {
        var selectors = [
            'form[action*="/shop/cart/update"]',
            '#add_to_cart',
            '.js_check_product',
            '.css_quantity',
            '.js_quantity',
            '.o_wsale_product_btn',
            'a.a-submit',
            '#product_details form.js_add_cart_json',
            '.oe_product_cart'
        ];

        selectors.forEach(function (selector) {
            var elements = document.querySelectorAll(selector);
            elements.forEach(function (el) {
                el.style.display = 'none';
            });
        });

        // Aussi ajouter une classe au body
        document.body.classList.add('storage-box-product');
    }

    /**
     * Crée le conteneur avec les boutons
     */
    function createButtonsContainer(data) {
        var container = document.createElement('div');
        container.className = 'storage-box-buttons-container my-4';
        container.id = 'storage_box_buttons';

        var html = '';

        // Badge de statut
        if (data.show_badge) {
            var badgeClass = 'secondary';
            var badgeIcon = 'fa-question';
            var badgeText = data.storage_status_display || 'Inconnu';

            switch (data.storage_status) {
                case 'available':
                    badgeClass = 'success';
                    badgeIcon = 'fa-check-circle';
                    break;
                case 'rented':
                    badgeClass = 'danger';
                    badgeIcon = 'fa-lock';
                    break;
                case 'reserved':
                    badgeClass = 'warning';
                    badgeIcon = 'fa-clock-o';
                    break;
                case 'maintenance':
                    badgeClass = 'secondary';
                    badgeIcon = 'fa-wrench';
                    break;
            }

            html += '<div class="storage-status-badge mb-3">';
            html += '<span class="badge text-bg-' + badgeClass + ' fs-5 px-4 py-2">';
            html += '<i class="fa ' + badgeIcon + ' me-2"></i>' + badgeText;
            html += '</span></div>';
        }

        // Bouton RDV (si disponible)
        if (data.show_appointment_button) {
            html += '<div class="storage-appointment-button mb-3">';
            html += '<a href="' + data.appointment_url + '" class="btn btn-primary btn-lg w-100 py-3">';
            html += '<i class="fa fa-calendar me-2"></i>';
            html += data.appointment_button_label;
            html += '</a>';
            html += '<p class="text-muted small mt-2 text-center mb-0">';
            html += '<i class="fa fa-info-circle me-1"></i>';
            html += 'Prenez rendez-vous pour visiter ce box';
            html += '</p></div>';
        }

        // Bouton Demande générale (si non disponible)
        if (data.show_general_inquiry_button) {
            html += '<div class="storage-general-inquiry-button mb-3">';
            html += '<a href="' + data.general_inquiry_url + '" class="btn btn-secondary btn-lg w-100 py-3">';
            html += '<i class="fa fa-envelope me-2"></i>';
            html += data.general_inquiry_button_label;
            html += '</a>';
            html += '<p class="text-muted small mt-2 text-center mb-0">';
            html += '<i class="fa fa-info-circle me-1"></i>';
            html += 'Ce box n\'est pas disponible. Contactez-nous pour plus d\'informations.';
            html += '</p></div>';
        }

        container.innerHTML = html;
        return container;
    }

    /**
     * Insère le conteneur au bon endroit dans la page
     */
    function insertContainer(container) {
        // Essayer différents emplacements possibles
        var targets = [
            // Après le prix
            '.product_price',
            '[itemprop="offers"]',
            // Après le formulaire panier (même s'il est masqué)
            'form[action*="/shop/cart/update"]',
            '.js_add_cart_json',
            // Dans la section produit
            '#product_details',
            '.o_wsale_product_page_view',
            // Fallback
            '#product_detail'
        ];

        for (var i = 0; i < targets.length; i++) {
            var target = document.querySelector(targets[i]);
            if (target) {
                // Insérer après l'élément trouvé
                target.parentNode.insertBefore(container, target.nextSibling);
                console.log('Lolirine Storage: Boutons insérés après', targets[i]);
                return;
            }
        }

        console.warn('Lolirine Storage: Impossible de trouver un emplacement pour les boutons');
    }
})();
