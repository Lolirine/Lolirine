/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

/**
 * Widget d'autocomplétion d'adresses avec Google Places API
 * Compatible avec les formulaires standards ET les wizards/modals
 * Utilisation: <field name="mon_champ" widget="address_autocomplete"/>
 */
export class AddressAutocompleteField extends CharField {
    static template = "km_expense.AddressAutocompleteField";
    
    setup() {
        super.setup();
        this.inputRef = useRef("input");
        this.orm = useService("orm");
        this.autocomplete = null;
        this.state = useState({ loaded: false, error: null });
        this.initAttempts = 0;
        this.maxAttempts = 25; // Augmenté pour les modals lents
        this.observer = null;
        this.isInModal = false;
        
        onMounted(() => {
            // Détecter si on est dans un modal
            this.isInModal = this.detectModal();
            // Délai plus long pour les modals
            const delay = this.isInModal ? 1000 : 300;
            setTimeout(() => this.initGooglePlaces(), delay);
        });
        
        onWillUnmount(() => {
            this.cleanup();
        });
    }
    
    detectModal() {
        // Vérifier si le widget est dans un modal Odoo
        try {
            const el = this.inputRef.el || document.querySelector(`[name="${this.props.name}"]`);
            if (el) {
                return !!el.closest('.modal, .o_dialog, .o_technical_modal, .modal-dialog');
            }
        } catch (e) {
            // Ignore
        }
        return false;
    }
    
    cleanup() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        if (this.autocomplete && window.google && window.google.maps) {
            try {
                google.maps.event.clearInstanceListeners(this.autocomplete);
            } catch (e) {
                // Ignore cleanup errors
            }
            this.autocomplete = null;
        }
    }
    
    async initGooglePlaces() {
        try {
            const apiKey = await this.getApiKey();
            
            if (!apiKey) {
                this.state.error = "Clé API non configurée";
                console.warn("KM Expense: Clé API Google non configurée. Allez dans Configuration > Paramètres > Indemnités Kilométriques");
                return;
            }
            
            if (!window.google || !window.google.maps || !window.google.maps.places) {
                await this.loadGoogleScript(apiKey);
            }
            
            await this.waitForInput();
            
            // Injecter le CSS pour le z-index (critique pour les modals)
            this.injectModalCSS();
            
            this.setupAutocomplete();
            this.state.loaded = true;
        } catch (e) {
            this.state.error = e.message;
            console.error("KM Expense: Erreur initialisation Google Places:", e);
        }
    }
    
    injectModalCSS() {
        // S'assurer que le dropdown Google Places apparaît au-dessus des modals Odoo
        const styleId = 'km-expense-pac-container-style';
        if (!document.getElementById(styleId)) {
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
                /* Google Places Autocomplete dropdown - doit être au-dessus des modals Odoo (z-index ~1055) */
                .pac-container {
                    z-index: 10500 !important;
                    background-color: white !important;
                    border-radius: 4px !important;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
                    border: 1px solid #ddd !important;
                    font-family: inherit !important;
                    margin-top: 2px !important;
                }
                .pac-item {
                    padding: 10px 12px !important;
                    cursor: pointer !important;
                    border-top: 1px solid #f0f0f0 !important;
                    line-height: 1.4 !important;
                }
                .pac-item:first-child {
                    border-top: none !important;
                }
                .pac-item:hover {
                    background-color: #f8f9fa !important;
                }
                .pac-item-selected {
                    background-color: #e9ecef !important;
                }
                .pac-item-query {
                    font-weight: 600 !important;
                    color: #212529 !important;
                }
                .pac-matched {
                    font-weight: 700 !important;
                }
                .pac-icon {
                    margin-right: 8px !important;
                }
                /* Fix pour les modals Odoo */
                .modal .pac-target-input,
                .o_dialog .pac-target-input,
                .o_technical_modal .pac-target-input {
                    z-index: 1 !important;
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    async waitForInput() {
        return new Promise((resolve, reject) => {
            const checkInput = () => {
                this.initAttempts++;
                const input = this.inputRef.el;
                
                // Vérifier que l'input existe ET est visible dans le DOM
                if (input && input.offsetParent !== null && input.offsetWidth > 0) {
                    resolve();
                } else if (this.initAttempts < this.maxAttempts) {
                    setTimeout(checkInput, 150);
                } else {
                    // Dernière tentative - chercher par nom
                    const fallbackInput = document.querySelector(`input[name="${this.props.name}"]`);
                    if (fallbackInput) {
                        resolve();
                    } else {
                        reject(new Error(`Input "${this.props.name}" non trouvé après ${this.maxAttempts} tentatives`));
                    }
                }
            };
            checkInput();
        });
    }
    
    async getApiKey() {
        try {
            const result = await this.orm.call(
                "ir.config_parameter",
                "get_param",
                ["km_expense.distance_api_key"]
            );
            return result || "";
        } catch (e) {
            console.error("KM Expense: Erreur récupération clé API:", e);
            return "";
        }
    }
    
    loadGoogleScript(apiKey) {
        return new Promise((resolve, reject) => {
            if (window.google && window.google.maps && window.google.maps.places) {
                resolve();
                return;
            }
            
            const existingScript = document.querySelector('script[src*="maps.googleapis.com"]');
            if (existingScript) {
                let attempts = 0;
                const checkGoogle = setInterval(() => {
                    attempts++;
                    if (window.google && window.google.maps && window.google.maps.places) {
                        clearInterval(checkGoogle);
                        resolve();
                    } else if (attempts > 50) {
                        clearInterval(checkGoogle);
                        reject(new Error("Timeout loading Google Maps"));
                    }
                }, 100);
                return;
            }
            
            const callbackName = `initGooglePlaces_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            window[callbackName] = () => {
                delete window[callbackName];
                resolve();
            };
            
            const script = document.createElement("script");
            script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=${callbackName}`;
            script.async = true;
            script.defer = true;
            
            script.onerror = () => {
                delete window[callbackName];
                reject(new Error("Échec du chargement de Google Maps. Vérifiez votre clé API."));
            };
            
            document.head.appendChild(script);
        });
    }
    
    setupAutocomplete() {
        const input = this.inputRef.el;
        if (!input) {
            console.warn("KM Expense: Input element non trouvé pour", this.props.name);
            return;
        }
        
        if (!window.google || !window.google.maps || !window.google.maps.places) {
            console.warn("KM Expense: Google Places API non chargée");
            return;
        }
        
        // Options pour l'autocomplétion - focus sur la Belgique et pays voisins
        const options = {
            types: ["address"],
            componentRestrictions: { country: ["be", "fr", "lu", "nl", "de"] },
            fields: ["formatted_address", "address_components", "geometry"],
        };
        
        try {
            this.autocomplete = new google.maps.places.Autocomplete(input, options);
            
            // Empêcher le formulaire de se soumettre lors de la sélection avec Enter
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    e.stopPropagation();
                    return false;
                }
            });
            
            // Re-bind sur focus (important pour les modals qui peuvent perdre le binding)
            input.addEventListener('focus', () => {
                if (this.autocomplete && window.google && window.google.maps) {
                    // Force le recalcul de la position du dropdown
                    setTimeout(() => {
                        google.maps.event.trigger(this.autocomplete, 'focus');
                    }, 100);
                }
            });
            
            // Écouter la sélection d'une adresse
            this.autocomplete.addListener("place_changed", () => {
                const place = this.autocomplete.getPlace();
                
                if (place && place.formatted_address) {
                    const newValue = place.formatted_address;
                    input.value = newValue;
                    
                    // Mettre à jour la valeur dans Odoo
                    this.props.record.update({ [this.props.name]: newValue });
                    
                    // Déclencher les événements pour qu'Odoo détecte le changement
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    console.log("KM Expense: Adresse sélectionnée:", newValue);
                }
            });
            
            console.log("KM Expense: Google Places autocomplete initialisé pour", this.props.name, this.isInModal ? "(dans modal)" : "(formulaire standard)");
        } catch (e) {
            console.error("KM Expense: Erreur setup autocomplete:", e);
        }
    }
}

AddressAutocompleteField.template = "km_expense.AddressAutocompleteField";

export const addressAutocompleteField = {
    ...charField,
    component: AddressAutocompleteField,
};

registry.category("fields").add("address_autocomplete", addressAutocompleteField);
