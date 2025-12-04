/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

/**
 * Widget d'autocomplétion d'adresses avec Google Places API
 * Utilisation: <field name="mon_champ" widget="address_autocomplete"/>
 */
export class AddressAutocompleteField extends CharField {
    static template = "km_expense.AddressAutocompleteField";
    
    setup() {
        super.setup();
        this.inputRef = useRef("input");
        this.orm = useService("orm");
        this.autocomplete = null;
        this.state = useState({ loaded: false });
        
        onMounted(async () => {
            await this.initGooglePlaces();
        });
        
        onWillUnmount(() => {
            this.cleanup();
        });
    }
    
    cleanup() {
        if (this.autocomplete && window.google && window.google.maps) {
            google.maps.event.clearInstanceListeners(this.autocomplete);
            this.autocomplete = null;
        }
    }
    
    async initGooglePlaces() {
        try {
            // Récupérer la clé API depuis les paramètres système
            const apiKey = await this.getApiKey();
            
            if (!apiKey) {
                console.warn("KM Expense: Clé API Google non configurée. Allez dans Configuration > Paramètres > Indemnités Kilométriques");
                return;
            }
            
            // Charger le script Google Places si pas déjà chargé
            if (!window.google || !window.google.maps || !window.google.maps.places) {
                await this.loadGoogleScript(apiKey);
            }
            
            this.setupAutocomplete();
            this.state.loaded = true;
        } catch (e) {
            console.error("KM Expense: Erreur initialisation Google Places:", e);
        }
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
            // Vérifier si déjà chargé
            if (window.google && window.google.maps && window.google.maps.places) {
                resolve();
                return;
            }
            
            // Vérifier si le script est déjà en cours de chargement
            const existingScript = document.querySelector('script[src*="maps.googleapis.com"]');
            if (existingScript) {
                // Attendre que Google soit disponible
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
            
            // Créer un nom de callback unique
            const callbackName = `initGooglePlaces_${Date.now()}`;
            
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
            console.warn("KM Expense: Input element not found");
            return;
        }
        
        if (!window.google || !window.google.maps || !window.google.maps.places) {
            console.warn("KM Expense: Google Places API not loaded");
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
            
            // Écouter la sélection d'une adresse
            this.autocomplete.addListener("place_changed", () => {
                const place = this.autocomplete.getPlace();
                
                if (place && place.formatted_address) {
                    // Mettre à jour la valeur du champ Odoo
                    const newValue = place.formatted_address;
                    this.props.record.update({ [this.props.name]: newValue });
                }
            });
            
            console.log("KM Expense: Google Places autocomplete initialisé avec succès");
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
