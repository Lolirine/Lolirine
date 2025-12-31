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
        this.maxAttempts = 25;
        this.isInModal = false;
        this.modalObserver = null;
        
        onMounted(() => {
            this.isInModal = this.detectModal();
            const delay = this.isInModal ? 1000 : 300;
            setTimeout(() => this.initGooglePlaces(), delay);
            
            if (this.isInModal) {
                this.setupModalCloseListener();
            }
        });
        
        onWillUnmount(() => {
            this.cleanup();
        });
    }
    
    detectModal() {
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
    
    setupModalCloseListener() {
        const modal = document.querySelector('.modal.show, .o_dialog');
        if (modal) {
            modal.addEventListener('hidden.bs.modal', () => this.cleanup());
            modal.addEventListener('hide.bs.modal', () => this.hidePacContainer());
        }
        
        this.modalObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.removedNodes) {
                    if (node.nodeType === 1 && (node.classList?.contains('modal') || node.classList?.contains('o_dialog'))) {
                        this.cleanup();
                    }
                }
            }
        });
        this.modalObserver.observe(document.body, { childList: true, subtree: true });
    }
    
    hidePacContainer() {
        const pacContainers = document.querySelectorAll('.pac-container');
        pacContainers.forEach(container => {
            container.style.display = 'none';
            container.style.visibility = 'hidden';
        });
    }
    
    cleanup() {
        if (this.modalObserver) {
            this.modalObserver.disconnect();
            this.modalObserver = null;
        }
        
        if (this.autocomplete && window.google && window.google.maps) {
            try {
                google.maps.event.clearInstanceListeners(this.autocomplete);
            } catch (e) {
                // Ignore
            }
            this.autocomplete = null;
        }
        
        this.removePacContainers();
    }
    
    removePacContainers() {
        const pacContainers = document.querySelectorAll('.pac-container');
        pacContainers.forEach(container => {
            const isOrphan = !document.querySelector('.pac-target-input:focus');
            if (isOrphan) {
                container.remove();
            }
        });
    }
    
    async initGooglePlaces() {
        try {
            const apiKey = await this.getApiKey();
            
            if (!apiKey) {
                this.state.error = "Clé API non configurée";
                console.warn("KM Expense: Clé API Google non configurée");
                return;
            }
            
            if (!window.google || !window.google.maps || !window.google.maps.places) {
                await this.loadGoogleScript(apiKey);
            }
            
            await this.waitForInput();
            this.injectModalCSS();
            this.setupAutocomplete();
            this.state.loaded = true;
        } catch (e) {
            this.state.error = e.message;
            console.error("KM Expense: Erreur initialisation Google Places:", e);
        }
    }
    
    injectModalCSS() {
        const styleId = 'km-expense-pac-container-style';
        if (!document.getElementById(styleId)) {
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
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
            `;
            document.head.appendChild(style);
        }
    }
    
    async waitForInput() {
        return new Promise((resolve, reject) => {
            const checkInput = () => {
                this.initAttempts++;
                const input = this.inputRef.el;
                
                if (input && input.offsetParent !== null && input.offsetWidth > 0) {
                    resolve();
                } else if (this.initAttempts < this.maxAttempts) {
                    setTimeout(checkInput, 150);
                } else {
                    const fallbackInput = document.querySelector(`input[name="${this.props.name}"]`);
                    if (fallbackInput) {
                        resolve();
                    } else {
                        reject(new Error(`Input "${this.props.name}" non trouvé`));
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
                reject(new Error("Échec du chargement de Google Maps"));
            };
            
            document.head.appendChild(script);
        });
    }
    
    setupAutocomplete() {
        const input = this.inputRef.el;
        if (!input || !window.google?.maps?.places) {
            console.warn("KM Expense: Setup impossible");
            return;
        }
        
        const options = {
            types: ["address"],
            componentRestrictions: { country: ["be", "fr", "lu", "nl", "de"] },
            fields: ["formatted_address", "address_components", "geometry"],
        };
        
        try {
            this.autocomplete = new google.maps.places.Autocomplete(input, options);
            
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    e.stopPropagation();
                    return false;
                }
            });
            
            input.addEventListener('blur', () => {
                setTimeout(() => {
                    if (!document.activeElement || document.activeElement !== input) {
                        this.hidePacContainer();
                    }
                }, 200);
            });
            
            input.addEventListener('focus', () => {
                if (this.autocomplete && window.google?.maps) {
                    setTimeout(() => {
                        google.maps.event.trigger(this.autocomplete, 'focus');
                    }, 100);
                }
            });
            
            this.autocomplete.addListener("place_changed", () => {
                const place = this.autocomplete.getPlace();
                
                if (place && place.formatted_address) {
                    const newValue = place.formatted_address;
                    input.value = newValue;
                    this.props.record.update({ [this.props.name]: newValue });
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    this.hidePacContainer();
                }
            });
            
            console.log("KM Expense: Autocomplete initialisé pour", this.props.name);
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
