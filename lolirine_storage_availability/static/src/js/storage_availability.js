/** @odoo-module **/

/**
 * Lolirine Storage Availability
 * Script pour masquer le bouton panier sur les box de stockage
 */

document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si on est sur une page produit
    const productDetail = document.getElementById('product_detail');
    if (!productDetail) return;

    // Vérifier si le produit est un box de stockage via les data attributes ou les snippets
    const storageBoxSection = document.querySelector('.s_storage_box_buttons, .s_storage_appointment_only, .s_storage_general_inquiry_only');
    const storageButton = document.querySelector('.storage-appointment-button a, .storage-general-inquiry-button a');
    
    // Si on a un snippet de box de stockage avec un bouton actif, masquer le panier
    if (storageButton && storageButton.href) {
        hideCartElements();
    }

    // Alternative: vérifier via un attribut data sur le body ou le produit
    const isStorageBox = document.body.dataset.isStorageBox === 'true' || 
                         productDetail.dataset.isStorageBox === 'true';
    
    if (isStorageBox) {
        hideCartElements();
    }

    /**
     * Masque tous les éléments du panier
     */
    function hideCartElements() {
        // Ajouter une classe au body pour le CSS
        document.body.classList.add('storage-box-product');

        // Masquer le formulaire d'ajout au panier
        const cartForms = document.querySelectorAll('form[action*="/shop/cart/update"]');
        cartForms.forEach(form => {
            form.style.display = 'none';
        });

        // Masquer le bouton "Ajouter au panier"
        const addToCartButtons = document.querySelectorAll('#add_to_cart, .js_check_product, .o_wsale_product_btn, a[href*="/shop/cart/update"]');
        addToCartButtons.forEach(btn => {
            btn.style.display = 'none';
        });

        // Masquer la section quantité
        const qtySection = document.querySelectorAll('.css_quantity, .input-group.js_quantity');
        qtySection.forEach(section => {
            section.style.display = 'none';
        });

        console.log('Lolirine Storage: Cart elements hidden for storage box product');
    }
});
