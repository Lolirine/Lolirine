/** @odoo-module **/

/**
 * Pool Store - Contact Form JavaScript
 * Gestion du formulaire de contact (toggle Particulier/Professionnel)
 */

document.addEventListener('DOMContentLoaded', function() {
    // Toggle champs professionnels
    const clientTypeInputs = document.querySelectorAll('input[name="client_type"]');
    const proFields = document.getElementById('professional_fields');
    const companyNameInput = document.querySelector('input[name="company_name"]');
    
    if (clientTypeInputs.length && proFields) {
        clientTypeInputs.forEach(function(input) {
            input.addEventListener('change', function() {
                if (this.value === 'professional') {
                    proFields.style.display = 'block';
                    if (companyNameInput) {
                        companyNameInput.setAttribute('required', 'required');
                    }
                } else {
                    proFields.style.display = 'none';
                    if (companyNameInput) {
                        companyNameInput.removeAttribute('required');
                        companyNameInput.value = '';
                    }
                    // Vider aussi le champ TVA
                    const vatInput = document.querySelector('input[name="vat_number"]');
                    if (vatInput) {
                        vatInput.value = '';
                    }
                }
            });
        });
    }
    
    // Animation des radio cards au clic
    const radioCards = document.querySelectorAll('.pool-radio-card');
    radioCards.forEach(function(card) {
        card.addEventListener('click', function() {
            // Retirer la classe active de toutes les cartes du même groupe
            const groupName = this.querySelector('input').name;
            document.querySelectorAll(`input[name="${groupName}"]`).forEach(function(input) {
                input.closest('.pool-radio-card').classList.remove('active');
            });
            // Ajouter la classe active à la carte cliquée
            this.classList.add('active');
        });
    });
    
    // Validation du formulaire
    const contactForm = document.querySelector('.pool-contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            // Vérifier que le type de demande est sélectionné
            const requestType = document.querySelector('input[name="request_type"]:checked');
            if (!requestType) {
                e.preventDefault();
                alert('Veuillez sélectionner un type de demande.');
                return false;
            }
            
            // Si professionnel, vérifier le nom d'entreprise
            const clientType = document.querySelector('input[name="client_type"]:checked');
            if (clientType && clientType.value === 'professional') {
                const companyName = document.querySelector('input[name="company_name"]');
                if (companyName && !companyName.value.trim()) {
                    e.preventDefault();
                    alert('Veuillez renseigner le nom de votre entreprise.');
                    companyName.focus();
                    return false;
                }
            }
            
            // Afficher indicateur de chargement
            const submitBtn = contactForm.querySelector('.pool-btn-submit');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Envoi en cours...';
                submitBtn.disabled = true;
            }
        });
    }
});
