/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Composant pour visualiser un catalogue avec formulaire d'extraction OCR amélioré.
 * Supporte l'extraction de produits simples et variantes, avec historique des captures.
 */
export class CatalogExtractorView extends Component {
    static template = "lolirine_pool_import.CatalogExtractorView";
    static props = {
        action: { type: Object },
        actionId: { type: Number, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            // Fournisseurs
            suppliers: [],
            selectedSupplier: null,
            
            // Visualisation catalogue
            catalogUrl: "",
            currentPage: 1,
            totalPages: 1,
            
            // OCR & Extraction
            ocrFile: null,
            ocrPreview: null,
            ocrLoading: false,
            ocrError: null,
            
            // Produits extraits (depuis la dernière extraction)
            extractedProducts: [],
            currentProductIndex: 0,
            extractionId: null,
            extractionType: 'single',
            
            // Formulaire (produit courant)
            formData: {
                supplier_ref: "",
                type_code: "",
                name: "",
                brand: "",
                category: "",
                subcategory: "",
                capacity: "",
                purchase_price: 0,
                selling_price: 0,
                // Champs calculés avec remise fournisseur
                discount_percent: 0,
                purchase_price_net: 0,
                selling_price_calculated: 0,
                description_fr: "",
                description_nl: "",
                // Spécifications techniques
                power_kw: 0,
                power_cv: "",
                voltage: 0,
                flow_rate: 0,
                cop: 0,
                noise_level: 0,
                // Attributs informatifs
                refrigerant_gas: "",
                power_supply: "",
                pool_volume_min: 0,
                pool_volume_max: 0,
                operating_temp_min: 0,
                operating_temp_max: 0,
                water_connection: "",
                energy_class: "",
                product_type: "",
                installation_type: "",
                wifi_compatible: false,
            },
            
            // Items ajoutés à importer
            items: [],
            loading: false,
            catalogId: null,
            
            // Historique des extractions
            extractionHistory: [],
            showHistory: false,
            
            // Onglet actif
            activeTab: 'form',
            
            // Recherche d'images Google
            imageSearch: {
                show: false,
                loading: false,
                query: '',
                results: [],
                selected: [],
                error: null,
            },
        });

        onWillStart(async () => {
            await this.loadSuppliers();
            await this.loadExtractionHistory();
        });

        onMounted(() => {
            this.setupKeyboardShortcuts();
        });
    }

    async loadSuppliers() {
        const suppliers = await this.orm.searchRead(
            "pool.supplier",
            [],
            ["id", "name", "code", "catalog_url"]
        );
        this.state.suppliers = suppliers;
        if (suppliers.length > 0) {
            this.selectSupplier(suppliers[0]);
        }
    }

    async loadExtractionHistory() {
        try {
            const extractions = await this.orm.searchRead(
                "pool.catalog.extraction",
                [['state', 'in', ['extracted', 'imported']]],
                ["id", "name", "create_date", "supplier_id", "extraction_type", "product_count", "imported_count", "state"],
                { limit: 20, order: "create_date desc" }
            );
            this.state.extractionHistory = extractions;
        } catch (e) {
            console.error("Error loading extraction history:", e);
        }
    }

    selectSupplier(supplier) {
        this.state.selectedSupplier = supplier;
        this.state.catalogUrl = supplier.catalog_url || "";
    }

    onSupplierChange(ev) {
        const supplierId = parseInt(ev.target.value);
        const supplier = this.state.suppliers.find(s => s.id === supplierId);
        if (supplier) {
            this.selectSupplier(supplier);
        }
    }

    onCatalogUrlChange(ev) {
        this.state.catalogUrl = ev.target.value;
    }

    loadCatalog() {
        const iframe = document.getElementById("catalog-viewer-iframe");
        if (iframe && this.state.catalogUrl) {
            iframe.src = this.state.catalogUrl;
        }
    }

    previousPage() {
        if (this.state.currentPage > 1) {
            this.state.currentPage--;
            this.updateCatalogPage();
        }
    }

    nextPage() {
        if (this.state.currentPage < this.state.totalPages) {
            this.state.currentPage++;
            this.updateCatalogPage();
        }
    }

    updateCatalogPage() {
        if (this.state.catalogUrl.includes("sibo.nl") || this.state.catalogUrl.includes("interactiv-doc")) {
            const baseUrl = this.state.catalogUrl.replace(/\/\d+\/?$/, "");
            const newUrl = `${baseUrl}/${this.state.currentPage}/`;
            const iframe = document.getElementById("catalog-viewer-iframe");
            if (iframe) {
                iframe.src = newUrl;
            }
        }
    }

    // ==================== Form Methods ====================

    onFormFieldChange(field, ev) {
        this.state.formData[field] = ev.target.value;
    }

    onPriceChange(field, ev) {
        this.state.formData[field] = parseFloat(ev.target.value) || 0;
    }

    onNumberChange(field, ev) {
        this.state.formData[field] = parseFloat(ev.target.value) || 0;
    }

    onCheckboxChange(field, ev) {
        this.state.formData[field] = ev.target.checked;
    }

    resetForm() {
        this.state.formData = {
            supplier_ref: "",
            type_code: "",
            name: "",
            brand: "",
            category: "",
            subcategory: "",
            capacity: "",
            purchase_price: 0,
            selling_price: 0,
            // Champs calculés avec remise fournisseur
            discount_percent: 0,
            purchase_price_net: 0,
            selling_price_calculated: 0,
            description_fr: "",
            description_nl: "",
            power_kw: 0,
            power_cv: "",
            voltage: 0,
            flow_rate: 0,
            cop: 0,
            noise_level: 0,
            // Attributs informatifs
            refrigerant_gas: "",
            power_supply: "",
            pool_volume_min: 0,
            pool_volume_max: 0,
            operating_temp_min: 0,
            operating_temp_max: 0,
            water_connection: "",
            energy_class: "",
            product_type: "",
            installation_type: "",
            wifi_compatible: false,
        };
        this.state.extractedProducts = [];
        this.state.currentProductIndex = 0;
        this.state.extractionId = null;
        this.state.ocrPreview = null;
        this.state.ocrFile = null;
        
        // Clear file input
        const fileInput = document.getElementById("ocr-file-input");
        if (fileInput) fileInput.value = "";
    }

    // ==================== OCR Methods ====================

    onOcrFileChange(ev) {
        const file = ev.target.files[0];
        if (file) {
            this.state.ocrFile = file;
            this.state.ocrError = null;
            
            const reader = new FileReader();
            reader.onload = (e) => {
                this.state.ocrPreview = e.target.result;
            };
            reader.readAsDataURL(file);
        }
    }

    async extractWithOcr() {
        if (!this.state.ocrFile) {
            this.state.ocrError = "Veuillez sélectionner une image";
            return;
        }

        this.state.ocrLoading = true;
        this.state.ocrError = null;

        try {
            const base64 = await this.fileToBase64(this.state.ocrFile);
            
            // Créer une extraction dans le backend
            const extractionId = await this.orm.call(
                "pool.catalog.extraction",
                "create_from_upload",
                [base64, this.state.selectedSupplier?.id, true]
            );
            
            // Récupérer l'extraction créée
            const extraction = await this.orm.read(
                "pool.catalog.extraction",
                [extractionId],
                ["id", "state", "extraction_type", "error_message", "raw_extraction_data"]
            );
            
            if (extraction[0].state === 'error') {
                this.state.ocrError = extraction[0].error_message || "Erreur lors de l'extraction";
                this.state.ocrLoading = false;
                return;
            }
            
            this.state.extractionId = extractionId;
            this.state.extractionType = extraction[0].extraction_type;
            
            // Récupérer les produits extraits
            const products = await this.orm.searchRead(
                "pool.catalog.extraction.product",
                [["extraction_id", "=", extractionId]],
                [
                    "id", "sequence", "name", "type_code", "reference", "brand", "category",
                    "variant_name", "capacity", "description_fr", "description_nl",
                    "purchase_price", "selling_price", "discount_percent", "purchase_price_net",
                    "selling_price_calculated", "power_kw", "power_cv", "voltage",
                    "flow_rate", "cop", "noise_level", "state"
                ],
                { order: "sequence" }
            );
            
            this.state.extractedProducts = products;
            this.state.currentProductIndex = 0;
            
            // Charger le premier produit dans le formulaire
            if (products.length > 0) {
                this.loadProductToForm(products[0]);
            }
            
            this.notification.add(
                _t(`${products.length} produit(s) extrait(s) !`),
                { type: "success" }
            );
            
            // Rafraîchir l'historique
            await this.loadExtractionHistory();
            
        } catch (error) {
            console.error("OCR Error:", error);
            this.state.ocrError = "Erreur: " + (error.message || error.data?.message || "Échec de l'extraction");
        }

        this.state.ocrLoading = false;
    }

    loadProductToForm(product) {
        this.state.formData = {
            supplier_ref: product.reference || "",
            type_code: product.type_code || "",
            name: product.name || "",
            brand: product.brand || "",
            category: product.category || "",
            subcategory: "",
            capacity: product.capacity || "",
            purchase_price: product.purchase_price || 0,
            selling_price: product.selling_price || 0,
            // Champs calculés avec remise fournisseur
            discount_percent: product.discount_percent || 0,
            purchase_price_net: product.purchase_price_net || 0,
            selling_price_calculated: product.selling_price_calculated || 0,
            description_fr: product.description_fr || "",
            description_nl: product.description_nl || "",
            power_kw: product.power_kw || 0,
            power_cv: product.power_cv || "",
            voltage: product.voltage || 0,
            flow_rate: product.flow_rate || 0,
            cop: product.cop || 0,
            noise_level: product.noise_level || 0,
            // Attributs informatifs
            refrigerant_gas: product.refrigerant_gas || "",
            power_supply: product.power_supply || "",
            pool_volume_min: product.pool_volume_min || 0,
            pool_volume_max: product.pool_volume_max || 0,
            operating_temp_min: product.operating_temp_min || 0,
            operating_temp_max: product.operating_temp_max || 0,
            water_connection: product.water_connection || "",
            energy_class: product.energy_class || "",
            product_type: product.product_type || "",
            installation_type: product.installation_type || "",
            wifi_compatible: product.wifi_compatible || false,
            // Garder une référence au produit extrait
            _extracted_product_id: product.id,
            _state: product.state,
        };
    }

    // Navigation entre les produits extraits
    previousProduct() {
        if (this.state.currentProductIndex > 0) {
            this.state.currentProductIndex--;
            this.loadProductToForm(this.state.extractedProducts[this.state.currentProductIndex]);
        }
    }

    nextProduct() {
        if (this.state.currentProductIndex < this.state.extractedProducts.length - 1) {
            this.state.currentProductIndex++;
            this.loadProductToForm(this.state.extractedProducts[this.state.currentProductIndex]);
        }
    }

    selectProduct(index) {
        if (index >= 0 && index < this.state.extractedProducts.length) {
            this.state.currentProductIndex = index;
            this.loadProductToForm(this.state.extractedProducts[index]);
        }
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                const base64 = reader.result.split(",")[1];
                resolve(base64);
            };
            reader.onerror = (error) => reject(error);
        });
    }

    // ==================== Import Methods ====================

    async addProduct() {
        if (!this.state.formData.supplier_ref && !this.state.formData.name) {
            this.notification.add(_t("Référence ou nom requis"), { type: "warning" });
            return;
        }

        this.state.loading = true;

        try {
            // Si on a un produit extrait, utiliser la méthode du backend
            if (this.state.formData._extracted_product_id) {
                console.log("Import produit extrait ID:", this.state.formData._extracted_product_id);
                
                const result = await this.orm.call(
                    "pool.catalog.extraction.product",
                    "action_import_to_odoo",
                    [[this.state.formData._extracted_product_id]]
                );
                
                console.log("Résultat import:", result);
                
                if (result === false) {
                    // L'import a échoué, récupérer le message d'erreur
                    const product = await this.orm.read(
                        "pool.catalog.extraction.product",
                        [this.state.formData._extracted_product_id],
                        ["state", "error_message"]
                    );
                    
                    const errorMsg = product[0]?.error_message || "Erreur inconnue lors de l'import";
                    this.notification.add(_t("Erreur: ") + errorMsg, { type: "danger" });
                    
                    // Mettre à jour l'état local
                    const idx = this.state.currentProductIndex;
                    if (this.state.extractedProducts[idx]) {
                        this.state.extractedProducts[idx].state = 'error';
                    }
                    this.state.formData._state = 'error';
                } else {
                    // Succès
                    const idx = this.state.currentProductIndex;
                    if (this.state.extractedProducts[idx]) {
                        this.state.extractedProducts[idx].state = 'imported';
                    }
                    this.state.formData._state = 'imported';
                    
                    this.notification.add(_t("Produit importé avec succès !"), { type: "success" });
                    
                    // Passer au produit suivant s'il y en a (qui n'est pas déjà importé)
                    const nextDraftIndex = this.state.extractedProducts.findIndex(
                        (p, i) => i > this.state.currentProductIndex && p.state === 'draft'
                    );
                    if (nextDraftIndex !== -1) {
                        this.selectProduct(nextDraftIndex);
                    }
                }
            } else {
                // Import manuel via catalog item
                if (!this.state.catalogId) {
                    const catalogId = await this.orm.create("pool.catalog", [{
                        name: `Import ${this.state.selectedSupplier?.name || "Manuel"} - ${new Date().toLocaleDateString()}`,
                        supplier_id: this.state.selectedSupplier?.id,
                        state: "loaded",
                    }]);
                    this.state.catalogId = catalogId;
                }

                const itemId = await this.orm.create("pool.catalog.item", [{
                    catalog_id: this.state.catalogId,
                    supplier_ref: this.state.formData.supplier_ref || this.state.formData.type_code,
                    name: this.state.formData.name,
                    brand: this.state.formData.brand,
                    category: this.state.formData.category,
                    subcategory: this.state.formData.subcategory,
                    purchase_price: this.state.formData.purchase_price,
                    selling_price: this.state.formData.selling_price,
                    description_fr: this.state.formData.description_fr,
                    description_nl: this.state.formData.description_nl,
                    state: "to_import",
                }]);

                this.state.items.push({
                    id: itemId,
                    ...this.state.formData,
                });

                this.notification.add(_t("Produit ajouté avec succès"), { type: "success" });
            }

            // Rafraîchir l'historique si nécessaire
            if (this.state.extractionId) {
                await this.loadExtractionHistory();
            }

        } catch (error) {
            console.error("Add product error:", error);
            this.notification.add(
                _t("Erreur: ") + (error.message || error.data?.message || "Erreur inconnue"), 
                { type: "danger" }
            );
        }

        this.state.loading = false;
    }

    async importAllExtracted() {
        if (this.state.extractedProducts.length === 0) {
            this.notification.add(_t("Aucun produit extrait"), { type: "warning" });
            return;
        }

        this.state.loading = true;

        try {
            const result = await this.orm.call(
                "pool.catalog.extraction",
                "action_import_all",
                [[this.state.extractionId]]
            );
            
            // Recharger les produits extraits pour avoir les états à jour
            const products = await this.orm.searchRead(
                "pool.catalog.extraction.product",
                [["extraction_id", "=", this.state.extractionId]],
                [
                    "id", "sequence", "name", "type_code", "reference", "brand", "category",
                    "variant_name", "capacity", "description_fr", "description_nl",
                    "purchase_price", "selling_price", "discount_percent", "purchase_price_net",
                    "selling_price_calculated", "power_kw", "power_cv", "voltage",
                    "flow_rate", "cop", "noise_level", "state", "product_id"
                ],
                { order: "sequence" }
            );
            
            this.state.extractedProducts = products;
            
            // Compter les produits importés
            const importedCount = products.filter(p => p.state === 'imported').length;
            
            // Si le résultat contient un res_id (cas des variantes), proposer d'ouvrir le produit
            if (result && result.res_id) {
                this.notification.add(
                    _t("Produit avec variantes créé ! Cliquez pour l'ouvrir."),
                    { 
                        type: "success",
                        sticky: true,
                        buttons: [{
                            name: _t("Ouvrir le produit"),
                            onClick: () => {
                                this.action.doAction({
                                    type: 'ir.actions.act_window',
                                    res_model: 'product.template',
                                    res_id: result.res_id,
                                    views: [[false, 'form']],
                                    target: 'current',
                                });
                            },
                            primary: true,
                        }],
                    }
                );
            } else {
                // Notification standard
                this.notification.add(
                    _t(`${importedCount} produit(s) importé(s)`),
                    { type: "success" }
                );
            }
            
            await this.loadExtractionHistory();
            
        } catch (error) {
            console.error("Import all error:", error);
            this.notification.add(
                _t("Erreur: ") + (error.message || error.data?.message || "Erreur inconnue"),
                { type: "danger" }
            );
        }

        this.state.loading = false;
    }

    selectItem(item) {
        this.state.formData = { ...item };
    }

    async deleteItem(item) {
        if (confirm(_t("Supprimer cet élément ?"))) {
            await this.orm.unlink("pool.catalog.item", [item.id]);
            this.state.items = this.state.items.filter(i => i.id !== item.id);
            this.notification.add(_t("Élément supprimé"), { type: "info" });
        }
    }

    async importAllItems() {
        if (this.state.items.length === 0) {
            this.notification.add(_t("Aucun élément à importer"), { type: "warning" });
            return;
        }

        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "pool.catalog",
            res_id: this.state.catalogId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ==================== History Methods ====================

    toggleHistory() {
        this.state.showHistory = !this.state.showHistory;
    }

    async loadExtraction(extractionId) {
        try {
            // Récupérer les produits de cette extraction
            const products = await this.orm.searchRead(
                "pool.catalog.extraction.product",
                [["extraction_id", "=", extractionId]],
                [
                    "id", "sequence", "name", "type_code", "reference", "brand", "category",
                    "variant_name", "capacity", "description_fr", "description_nl",
                    "purchase_price", "selling_price", "discount_percent", "purchase_price_net",
                    "selling_price_calculated", "power_kw", "power_cv", "voltage",
                    "flow_rate", "cop", "noise_level", "state"
                ],
                { order: "sequence" }
            );
            
            const extraction = await this.orm.read(
                "pool.catalog.extraction",
                [extractionId],
                ["extraction_type", "image"]
            );
            
            this.state.extractedProducts = products;
            this.state.currentProductIndex = 0;
            this.state.extractionId = extractionId;
            this.state.extractionType = extraction[0].extraction_type;
            
            if (extraction[0].image) {
                this.state.ocrPreview = `data:image/png;base64,${extraction[0].image}`;
            }
            
            if (products.length > 0) {
                this.loadProductToForm(products[0]);
            }
            
            this.state.showHistory = false;
            this.notification.add(_t(`${products.length} produit(s) chargé(s)`), { type: "info" });
            
        } catch (error) {
            console.error("Load extraction error:", error);
            this.notification.add(_t("Erreur lors du chargement"), { type: "danger" });
        }
    }

    // ==================== Navigation Methods ====================

    openCatalogList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "pool.catalog",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openExtractionList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "pool.catalog.extraction",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    setActiveTab(tab) {
        this.state.activeTab = tab;
    }

    setupKeyboardShortcuts() {
        document.addEventListener("keydown", (ev) => {
            if (ev.ctrlKey && ev.key === "Enter") {
                this.addProduct();
            }
            // Navigation produits avec flèches
            if (ev.altKey && ev.key === "ArrowLeft") {
                this.previousProduct();
            }
            if (ev.altKey && ev.key === "ArrowRight") {
                this.nextProduct();
            }
        });
    }

    // ==================== Getters for template ====================

    get currentProduct() {
        return this.state.extractedProducts[this.state.currentProductIndex];
    }

    get hasMultipleProducts() {
        return this.state.extractedProducts.length > 1;
    }

    get productNavigationText() {
        const total = this.state.extractedProducts.length;
        const current = this.state.currentProductIndex + 1;
        return total > 0 ? `${current} / ${total}` : "0 / 0";
    }

    get pendingProductsCount() {
        return this.state.extractedProducts.filter(p => p.state === 'draft').length;
    }
    
    get isCurrentProductImported() {
        return this.state.formData._state === 'imported';
    }
    
    // ==================== Image Search Methods ====================
    
    async openImageSearch() {
        const currentProduct = this.currentProduct;
        if (!currentProduct) {
            this.notification.add("Veuillez d'abord extraire un produit", { type: "warning" });
            return;
        }
        
        // Réinitialiser et ouvrir le panneau
        this.state.imageSearch = {
            show: true,
            loading: true,
            query: '',
            results: [],
            selected: [],
            error: null,
        };
        
        try {
            const result = await this.orm.call(
                'pool.catalog.extraction.product',
                'search_images_for_product',
                [currentProduct.id]
            );
            
            if (result.success) {
                this.state.imageSearch.results = result.images || [];
                this.state.imageSearch.query = result.query || '';
                this.state.imageSearch.error = null;
            } else {
                this.state.imageSearch.error = result.error || 'Erreur inconnue';
            }
        } catch (error) {
            console.error("Erreur recherche images:", error);
            this.state.imageSearch.error = error.message || 'Erreur de connexion';
        } finally {
            this.state.imageSearch.loading = false;
        }
    }
    
    closeImageSearch() {
        this.state.imageSearch.show = false;
    }
    
    toggleImageSelection(index) {
        const selected = this.state.imageSearch.selected;
        const pos = selected.indexOf(index);
        
        if (pos > -1) {
            selected.splice(pos, 1);
        } else {
            selected.push(index);
        }
        
        // Force reactivity
        this.state.imageSearch.selected = [...selected];
    }
    
    isImageSelected(index) {
        return this.state.imageSearch.selected.includes(index);
    }
    
    selectAllImages() {
        const allIndexes = this.state.imageSearch.results.map((_, i) => i);
        this.state.imageSearch.selected = allIndexes;
    }
    
    deselectAllImages() {
        this.state.imageSearch.selected = [];
    }
    
    async importSelectedImages() {
        const currentProduct = this.currentProduct;
        if (!currentProduct) {
            this.notification.add("Aucun produit sélectionné", { type: "warning" });
            return;
        }
        
        const selectedIndexes = this.state.imageSearch.selected;
        if (selectedIndexes.length === 0) {
            this.notification.add("Sélectionnez au moins une image", { type: "warning" });
            return;
        }
        
        // Préparer les URLs des images sélectionnées
        const imageUrls = selectedIndexes.map(idx => {
            const img = this.state.imageSearch.results[idx];
            return {
                url: img.url,
                title: img.title || `Image ${idx + 1}`,
            };
        });
        
        this.state.imageSearch.loading = true;
        
        try {
            const result = await this.orm.call(
                'pool.catalog.extraction.product',
                'import_images_for_product',
                [currentProduct.id, imageUrls]
            );
            
            if (result.success) {
                this.notification.add(result.message, { type: "success" });
                this.closeImageSearch();
            } else {
                this.notification.add(result.error || 'Erreur import', { type: "danger" });
            }
        } catch (error) {
            console.error("Erreur import images:", error);
            this.notification.add(error.message || 'Erreur de connexion', { type: "danger" });
        } finally {
            this.state.imageSearch.loading = false;
        }
    }
    
    async searchImagesWithCustomQuery() {
        // Permet de refaire une recherche avec une query personnalisée
        const query = this.state.imageSearch.query;
        if (!query) return;
        
        const currentProduct = this.currentProduct;
        if (!currentProduct) return;
        
        this.state.imageSearch.loading = true;
        this.state.imageSearch.selected = [];
        
        try {
            // Appel direct à Google via le backend avec query custom
            const result = await this.orm.call(
                'pool.catalog.extraction.product',
                'search_images_custom_query',
                [currentProduct.id, query]
            );
            
            if (result.success) {
                this.state.imageSearch.results = result.images || [];
                this.state.imageSearch.error = null;
            } else {
                this.state.imageSearch.error = result.error || 'Erreur inconnue';
            }
        } catch (error) {
            this.state.imageSearch.error = error.message || 'Erreur de connexion';
        } finally {
            this.state.imageSearch.loading = false;
        }
    }
    
    onImageSearchQueryChange(ev) {
        this.state.imageSearch.query = ev.target.value;
    }
    
    onImageSearchKeydown(ev) {
        if (ev.key === 'Enter') {
            this.searchImagesWithCustomQuery();
        }
    }
}

// Enregistrer le composant comme action client
registry.category("actions").add("pool_catalog_extractor", CatalogExtractorView);
