/** @odoo-module **/
/*
 * Matériaux bâtiment — visionneuse des sites fournisseurs (Carlier, Gobert…).
 * À gauche : le devis ou l'ouvrage ouvert, l'import d'un article par sa référence
 * ou l'adresse de sa page, et les matériaux déjà dans Odoo ; à droite : le site.
 */
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const MODELE = "product.template";

export class BatFournisseurs extends Component {
    static template = "lolirine_batiment.BatFournisseurs";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
        const p = (this.props.action && this.props.action.params) || {};
        this.params = p;
        this.state = useState({
            chargement: true,
            data: null,
            fournisseur: null,
            recherche: "",
            url: "",
            importTexte: "",
            importe: null,
            importEnCours: false,
            filtre: "",
            qte: {},
        });
        onWillStart(async () => {
            const d = await this.orm.call(MODELE, "bat_visionneuse_donnees",
                [p.produit_id || false, p.res_model || false, p.res_id || false]);
            this.state.data = d;
            const prod = d.produit;
            const f = (prod && d.fournisseurs.find((x) => x.id === prod.fournisseur_id)) || d.fournisseurs[0] || null;
            this.state.fournisseur = f;
            if (prod && prod.url) {
                this.state.url = prod.url;
            } else if (prod && f) {
                this.chercher(prod.ref || prod.nom);
            } else if (f) {
                this.state.url = f.site || "";
            }
            this.state.chargement = false;
        });
    }

    fmt(v) {
        return (v || 0).toLocaleString("fr-BE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
    }
    libelleMaj(m) {
        return m && m !== "0" ? "+" + m + " %" : "";
    }
    get cibleLibelle() {
        const c = this.state.data && this.state.data.cible;
        if (!c) return "";
        return c.model === "sale.order" ? "au devis" : "à l'ouvrage";
    }
    get titreCible() {
        const c = this.state.data && this.state.data.cible;
        return c && c.model === "sale.order" ? "Matériaux du devis" : "Fournitures de l'ouvrage";
    }
    get materiaux() {
        const t = (this.state.filtre || "").toLowerCase();
        const liste = this.state.data.materiaux || [];
        return t ? liste.filter((m) => (m.nom + " " + m.code + " " + m.ref + " " + m.fournisseur).toLowerCase().includes(t)) : liste;
    }

    choisirFournisseur(f) {
        this.state.fournisseur = f;
        if (this.state.recherche) {
            this.chercher(this.state.recherche);
        } else {
            this.state.url = f.site || "";
        }
    }
    chercher(texte) {
        const f = this.state.fournisseur;
        if (texte !== undefined) this.state.recherche = texte;
        if (!f) return;
        const t = encodeURIComponent(this.state.recherche || "");
        this.state.url = f.recherche ? f.recherche.replace("{}", t) : f.site;
    }
    montrer(m) {
        const f = this.state.data.fournisseurs.find((x) => x.id === m.fournisseur_id);
        if (f) this.state.fournisseur = f;
        if (m.url) {
            this.state.url = m.url;
        } else {
            this.chercher(m.ref || m.nom);
        }
    }
    async importer() {
        const f = this.state.fournisseur;
        if (!f || !this.state.importTexte) return;
        this.state.importEnCours = true;
        try {
            const r = await this.orm.call(MODELE, "bat_importer_article", [f.id, this.state.importTexte]);
            this.state.importe = r;
            if (r.url) this.state.url = r.url;
            const liste = this.state.data.materiaux;
            const i = liste.findIndex((x) => x.id === r.id);
            if (i >= 0) liste[i] = r; else liste.unshift(r);
            this.notification.add(r.nouveau ? "Article créé dans Odoo : " + r.nom : "Prix relu : " + r.nom,
                { type: r.avertissement ? "warning" : "success" });
            if (r.avertissement) this.notification.add(r.avertissement, { type: "warning" });
        } finally {
            this.state.importEnCours = false;
        }
    }
    async appliquer(m) {
        await this.orm.call(MODELE, "action_bat_appliquer_prix", [[m.id]]);
        const d = await this.orm.call(MODELE, "bat_visionneuse_donnees", [m.id, false, false]);
        const liste = this.state.data.materiaux;
        const i = liste.findIndex((x) => x.id === m.id);
        if (i >= 0) liste[i] = d.produit;
        if (this.state.importe && this.state.importe.id === m.id) this.state.importe = d.produit;
        this.notification.add("Prix appliqué : " + m.nom, { type: "success" });
    }
    async ajouter(m) {
        const c = this.state.data.cible;
        if (!c) return;
        const q = parseFloat(this.state.qte[m.id] || 1) || 1;
        c.lignes = await this.orm.call(MODELE, "bat_ajouter", [c.model, c.id, m.id, q]);
        this.notification.add(m.nom + " ajouté " + this.cibleLibelle + " (" + q + ")", { type: "success" });
    }
    ouvrirFiche(m) {
        this.actionService.doAction({
            type: "ir.actions.act_window", res_model: MODELE, res_id: m.id,
            views: [[false, "form"]], target: "current",
        });
    }
    retour() {
        const c = this.state.data.cible;
        if (c) {
            this.actionService.doAction({
                type: "ir.actions.act_window", res_model: c.model, res_id: c.id,
                views: [[false, "form"]], target: "current",
            });
        } else {
            this.actionService.restore();
        }
    }
}

registry.category("actions").add("lolirine_bat_fournisseurs", BatFournisseurs);
