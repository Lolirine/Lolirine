/** @odoo-module **/

document.addEventListener('DOMContentLoaded', function() {
    
    // === Toggle champs entreprise ===
    const isCompanyCheckbox = document.getElementById('is_company');
    const companyFields = document.getElementById('company_fields');
    const companyNameInput = document.getElementById('company_name');
    const legalNameInput = document.getElementById('legal_name');
    const vatInput = document.getElementById('vat_input');
    const contactPersonInput = document.getElementById('contact_person');
    
    if (isCompanyCheckbox && companyFields) {
        isCompanyCheckbox.addEventListener('change', function() {
            if (this.checked) {
                companyFields.classList.remove('d-none');
                // Rendre les champs obligatoires
                if (companyNameInput) companyNameInput.required = true;
                if (legalNameInput) legalNameInput.required = true;
                if (vatInput) vatInput.required = true;
                if (contactPersonInput) contactPersonInput.required = true;
            } else {
                companyFields.classList.add('d-none');
                // Retirer l'obligation
                if (companyNameInput) companyNameInput.required = false;
                if (legalNameInput) legalNameInput.required = false;
                if (vatInput) vatInput.required = false;
                if (contactPersonInput) contactPersonInput.required = false;
            }
        });
    }
    
    // === Google Places Autocomplete ===
    const addressSearch = document.getElementById('address_search');
    const addressSuggestions = document.getElementById('address_suggestions');
    const streetInput = document.getElementById('street');
    const streetNumberInput = document.getElementById('street_number');
    const zipInput = document.getElementById('zip');
    const cityInput = document.getElementById('city');
    
    let searchTimeout = null;
    let googleApiKey = null;
    
    // Récupérer la clé API Google depuis Odoo
    async function getGoogleApiKey() {
        try {
            const response = await fetch('/api/config/google-api-key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}, id: 1})
            });
            const data = await response.json();
            if (data.result && data.result.api_key) {
                googleApiKey = data.result.api_key;
                initGoogleAutocomplete();
            } else {
                console.warn('Clé API Google non configurée, autocomplétion désactivée');
                // Fallback: cacher le champ de recherche ou afficher un message
                if (addressSearch) {
                    addressSearch.placeholder = 'Entrez votre adresse manuellement';
                }
            }
        } catch (error) {
            console.error('Erreur lors de la récupération de la clé API:', error);
        }
    }
    
    // Initialiser Google Places Autocomplete
    function initGoogleAutocomplete() {
        if (!googleApiKey || !addressSearch) return;
        
        // Charger le script Google Places
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${googleApiKey}&libraries=places&callback=initAutocomplete`;
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
    }
    
    // Callback Google Places
    window.initAutocomplete = function() {
        if (!addressSearch) return;
        
        const autocomplete = new google.maps.places.Autocomplete(addressSearch, {
            types: ['address'],
            componentRestrictions: { country: ['be', 'fr', 'lu', 'nl', 'de'] },
            fields: ['address_components', 'formatted_address']
        });
        
        autocomplete.addListener('place_changed', function() {
            const place = autocomplete.getPlace();
            
            if (!place.address_components) {
                return;
            }
            
            // Réinitialiser les champs
            if (streetInput) streetInput.value = '';
            if (streetNumberInput) streetNumberInput.value = '';
            if (zipInput) zipInput.value = '';
            if (cityInput) cityInput.value = '';
            
            // Remplir les champs avec les composants d'adresse
            for (const component of place.address_components) {
                const type = component.types[0];
                
                switch (type) {
                    case 'street_number':
                        if (streetNumberInput) streetNumberInput.value = component.long_name;
                        break;
                    case 'route':
                        if (streetInput) streetInput.value = component.long_name;
                        break;
                    case 'postal_code':
                        if (zipInput) zipInput.value = component.long_name;
                        break;
                    case 'locality':
                    case 'sublocality':
                    case 'postal_town':
                        if (cityInput && !cityInput.value) cityInput.value = component.long_name;
                        break;
                }
            }
            
            // Focus sur le premier champ vide
            if (streetNumberInput && !streetNumberInput.value) {
                streetNumberInput.focus();
            } else if (zipInput && !zipInput.value) {
                zipInput.focus();
            }
        });
    };
    
    // Lancer la récupération de la clé API
    if (addressSearch) {
        getGoogleApiKey();
    }
    
    // === Validation TVA ===
    const validateVatBtn = document.getElementById('validate_vat_btn');
    const vatFeedback = document.getElementById('vat_feedback');
    
    if (validateVatBtn && vatInput && vatFeedback) {
        validateVatBtn.addEventListener('click', function() {
            const vat = vatInput.value.trim();
            
            if (!vat) {
                vatFeedback.innerHTML = '<span class="text-warning">Veuillez entrer un numéro de TVA</span>';
                return;
            }
            
            // Validation basique du format belge
            let cleanVat = vat.replace(/[\s.-]/g, '');
            if (!cleanVat.startsWith('BE')) {
                cleanVat = 'BE' + cleanVat;
            }
            
            // Format attendu: BE + 10 chiffres
            const regex = /^BE[01]?\d{9,10}$/;
            
            if (regex.test(cleanVat)) {
                vatFeedback.innerHTML = '<span class="text-success"><i class="fa fa-check"></i> Format valide</span>';
                vatInput.value = cleanVat.replace(/^BE/, '').replace(/(\d{4})(\d{3})(\d{3})/, '$1.$2.$3');
                vatInput.classList.remove('is-invalid');
                vatInput.classList.add('is-valid');
            } else {
                vatFeedback.innerHTML = '<span class="text-danger"><i class="fa fa-times"></i> Format invalide (ex: 0123.456.789)</span>';
                vatInput.classList.remove('is-valid');
                vatInput.classList.add('is-invalid');
            }
        });
        
        // Validation en temps réel
        vatInput.addEventListener('input', function() {
            vatFeedback.innerHTML = '';
            vatInput.classList.remove('is-valid', 'is-invalid');
        });
    }
    
    // === Validation du formulaire ===
    const form = document.getElementById('lolirine_contact_form');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            // Vérifier les champs société si coché
            if (isCompanyCheckbox && isCompanyCheckbox.checked) {
                let valid = true;
                const requiredFields = [companyNameInput, legalNameInput, vatInput, contactPersonInput];
                
                requiredFields.forEach(function(field) {
                    if (field && !field.value.trim()) {
                        field.classList.add('is-invalid');
                        valid = false;
                    } else if (field) {
                        field.classList.remove('is-invalid');
                    }
                });
                
                if (!valid) {
                    e.preventDefault();
                    alert('Veuillez remplir tous les champs obligatoires pour une société.');
                    return false;
                }
            }
            
            // Nettoyer le numéro de téléphone
            const mobileInput = form.querySelector('input[name="mobile"]');
            if (mobileInput && mobileInput.value) {
                let phone = mobileInput.value.replace(/[\s.-]/g, '');
                if (phone.startsWith('0')) {
                    phone = '+32' + phone.substring(1);
                }
                mobileInput.value = phone;
            }
        });
    }
    
    // === Date picker - définir la date minimum à aujourd'hui ===
    const startDateInput = document.querySelector('input[name="start_date"]');
    if (startDateInput) {
        const today = new Date().toISOString().split('T')[0];
        startDateInput.setAttribute('min', today);
    }
    
});
