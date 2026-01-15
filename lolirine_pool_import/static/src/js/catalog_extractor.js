/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Composant pour visualiser un catalogue avec formulaire d'extraction
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
            suppliers: [],
            selectedSupplier: null,
            catalogUrl: "",
            currentPage: 1,
            totalPages: 1,
            items: [],
            selectedItem: null,
            formData: {
                supplier_ref: "",
                name: "",
                brand: "",
                category: "",
                subcategory: "",
                purchase_price: 0,
                selling_price: 0,
                description_fr: "",
                description_nl: "",
            },
            loading: false,
            catalogId: null,
        });

        onWillStart(async () => {
            await this.loadSuppliers();
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
        // Recharger l'iframe avec l'URL du catalogue
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
        // Pour les catalogues Interactiv-Doc, on peut changer la page via l'URL
        if (this.state.catalogUrl.includes("sibo.nl") || this.state.catalogUrl.includes("interactiv-doc")) {
            const baseUrl = this.state.catalogUrl.replace(/\/\d+\/?$/, "");
            const newUrl = `${baseUrl}/${this.state.currentPage}/`;
            const iframe = document.getElementById("catalog-viewer-iframe");
            if (iframe) {
                iframe.src = newUrl;
            }
        }
    }

    onFormFieldChange(field, ev) {
        this.state.formData[field] = ev.target.value;
    }

    onPriceChange(field, ev) {
        this.state.formData[field] = parseFloat(ev.target.value) || 0;
    }

    async addProduct() {
        if (!this.state.formData.supplier_ref || !this.state.formData.name) {
            this.notification.add(_t("Référence et nom sont requis"), { type: "warning" });
            return;
        }

        this.state.loading = true;

        try {
            // Créer ou récupérer le catalogue
            if (!this.state.catalogId) {
                const catalogId = await this.orm.create("pool.catalog", [{
                    name: `Import ${this.state.selectedSupplier?.name || "Manuel"} - ${new Date().toLocaleDateString()}`,
                    supplier_id: this.state.selectedSupplier?.id,
                    state: "loaded",
                }]);
                this.state.catalogId = catalogId;
            }

            // Créer l'élément du catalogue
            const itemId = await this.orm.create("pool.catalog.item", [{
                catalog_id: this.state.catalogId,
                supplier_ref: this.state.formData.supplier_ref,
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

            // Ajouter à la liste
            this.state.items.push({
                id: itemId,
                ...this.state.formData,
            });

            // Réinitialiser le formulaire
            this.resetForm();

            this.notification.add(_t("Produit ajouté avec succès"), { type: "success" });

        } catch (error) {
            this.notification.add(_t("Erreur: ") + error.message, { type: "danger" });
        }

        this.state.loading = false;
    }

    resetForm() {
        this.state.formData = {
            supplier_ref: "",
            name: "",
            brand: "",
            category: "",
            subcategory: "",
            purchase_price: 0,
            selling_price: 0,
            description_fr: "",
            description_nl: "",
        };
    }

    selectItem(item) {
        this.state.selectedItem = item;
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

        this.state.loading = true;

        try {
            // Ouvrir le catalogue créé
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "pool.catalog",
                res_id: this.state.catalogId,
                views: [[false, "form"]],
                target: "current",
            });
        } catch (error) {
            this.notification.add(_t("Erreur: ") + error.message, { type: "danger" });
        }

        this.state.loading = false;
    }

    openCatalogList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "pool.catalog",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener("keydown", (ev) => {
            if (ev.ctrlKey && ev.key === "Enter") {
                this.addProduct();
            }
        });
    }
}

// Enregistrer le composant comme action client
registry.category("actions").add("pool_catalog_extractor", CatalogExtractorView);
