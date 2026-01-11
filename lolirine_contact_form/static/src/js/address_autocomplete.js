/** @odoo-module **/

document.addEventListener('DOMContentLoaded', function() {
    
    // === Toggle champs entreprise ===
    const isCompanyCheckbox = document.getElementById('is_company');
    const companyFields = document.getElementById('company_fields');
    
    if (isCompanyCheckbox && companyFields) {
        isCompanyCheckbox.addEventListener('change', function() {
            if (this.checked) {
                companyFields.classList.remove('d-none');
            } else {
                companyFields.classList.add('d-none');
            }
        });
    }
    
    // === Autocomplétion d'adresse ===
    const addressSearch = document.getElementById('address_search');
    const addressSuggestions = document.getElementById('address_suggestions');
    const streetInput = document.getElementById('street');
    const streetNumberInput = document.getElementById('street_number');
    const zipInput = document.getElementById('zip');
    const cityInput = document.getElementById('city');
    
    let searchTimeout = null;
    
    if (addressSearch && addressSuggestions) {
        
        // Recherche d'adresse
        addressSearch.addEventListener('input', function() {
            const query = this.value.trim();
            
            // Annuler la recherche précédente
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            
            // Masquer les suggestions si la requête est trop courte
            if (query.length < 3) {
                addressSuggestions.style.display = 'none';
                return;
            }
            
            // Délai pour éviter trop de requêtes
            searchTimeout = setTimeout(function() {
                fetchAddressSuggestions(query);
            }, 300);
        });
        
        // Masquer les suggestions quand on clique ailleurs
        document.addEventListener('click', function(e) {
            if (!addressSearch.contains(e.target) && !addressSuggestions.contains(e.target)) {
                addressSuggestions.style.display = 'none';
            }
        });
    }
    
    async function fetchAddressSuggestions(query) {
        try {
            // Utiliser l'API Nominatim directement (côté client)
            const countrySelect = document.getElementById('country_id');
            let countryCode = 'BE';
            
            // Récupérer le code pays si possible
            if (countrySelect) {
                const selectedOption = countrySelect.options[countrySelect.selectedIndex];
                if (selectedOption && selectedOption.text) {
                    // Mapping simple des pays courants
                    const countryMap = {
                        'Belgique': 'BE',
                        'Belgium': 'BE',
                        'France': 'FR',
                        'Luxembourg': 'LU',
                        'Pays-Bas': 'NL',
                        'Netherlands': 'NL',
                        'Allemagne': 'DE',
                        'Germany': 'DE',
                    };
                    countryCode = countryMap[selectedOption.text] || 'BE';
                }
            }
            
            const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&countrycodes=${countryCode}&format=json&addressdetails=1&limit=5`;
            
            const response = await fetch(url, {
                headers: {
                    'User-Agent': 'Lolirine-Website/1.0'
                }
            });
            
            const data = await response.json();
            
            displayAddressSuggestions(data);
            
        } catch (error) {
            console.error('Erreur lors de la recherche d\'adresse:', error);
        }
    }
    
    function displayAddressSuggestions(results) {
        addressSuggestions.innerHTML = '';
        
        if (results.length === 0) {
            addressSuggestions.style.display = 'none';
            return;
        }
        
        results.forEach(function(item) {
            const address = item.address || {};
            const div = document.createElement('a');
            div.href = '#';
            div.className = 'list-group-item list-group-item-action';
            div.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <span class="mb-0">${item.display_name}</span>
                </div>
            `;
            
            div.addEventListener('click', function(e) {
                e.preventDefault();
                selectAddress(item);
            });
            
            addressSuggestions.appendChild(div);
        });
        
        addressSuggestions.style.display = 'block';
    }
    
    function selectAddress(item) {
        const address = item.address || {};
        
        // Remplir les champs
        if (streetInput) {
            streetInput.value = address.road || address.street || '';
        }
        if (streetNumberInput) {
            streetNumberInput.value = address.house_number || '';
        }
        if (zipInput) {
            zipInput.value = address.postcode || '';
        }
        if (cityInput) {
            cityInput.value = address.city || address.town || address.village || address.municipality || '';
        }
        
        // Vider le champ de recherche et masquer les suggestions
        addressSearch.value = '';
        addressSuggestions.style.display = 'none';
        
        // Focus sur le champ suivant vide
        if (!streetNumberInput.value) {
            streetNumberInput.focus();
        } else if (!zipInput.value) {
            zipInput.focus();
        }
    }
    
    // === Validation TVA ===
    const vatInput = document.getElementById('vat_input');
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
            } else {
                vatFeedback.innerHTML = '<span class="text-danger"><i class="fa fa-times"></i> Format invalide (ex: 0123.456.789)</span>';
            }
        });
        
        // Validation en temps réel
        vatInput.addEventListener('input', function() {
            vatFeedback.innerHTML = '';
        });
    }
    
    // === Validation du formulaire ===
    const form = document.getElementById('lolirine_contact_form');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            // Validation supplémentaire si nécessaire
            const mobileInput = form.querySelector('input[name="mobile"]');
            if (mobileInput && mobileInput.value) {
                // Nettoyer le numéro de téléphone
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
