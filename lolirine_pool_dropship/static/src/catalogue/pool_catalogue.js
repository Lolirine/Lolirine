/** @odoo-module **/
/*
 * Pool Store — visionneuse des catalogues fournisseurs (SCP en PDF, Fluidra en flipbook)
 * ouverte depuis un devis piscine ou un bon de commande fournisseur.
 * À gauche : les lignes du document (référence, prix de la ligne, prix et page du
 * catalogue d'après l'index), la recherche et les rubriques ; à droite : la page.
 */
import { Component, onMounted, onPatched, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const MODELE = "pool.catalogue.mixin";
// import dynamique d'un module ES (pdf.js livré avec Odoo), hors transpilation des assets
const importDynamique = new Function("u", "return import(u)");
let pdfjs = null;
function chargerPdfjs() {
    if (!pdfjs) {
        pdfjs = importDynamique("/web/static/lib/pdfjs/build/pdf.js").then((L) => {
            L.GlobalWorkerOptions.workerSrc = "/web/static/lib/pdfjs/build/pdf.worker.js";
            return L;
        });
    }
    return pdfjs;
}
const documentsPdf = {};

function norm(c) {
    return (c || "").toUpperCase().replace(/^POOL-/, "").replace(/[\s\-/.]/g, "");
}

export class PoolCatalogue extends Component {
    static template = "lolirine_pool_dropship.PoolCatalogue";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.canvas = useRef("canvas");
        this.calque = useRef("calque");
        this.zone = useRef("zone");
        this.feuilleFlip = useRef("feuilleFlip");
        this.calqueSvg = useRef("calqueSvg");
        const p = (this.props.action && this.props.action.params) || {};
        this.resModel = p.res_model;
        this.resId = p.res_id;
        this.state = useState({
            chargement: true,
            data: null,
            cat: "scp",
            page: 1,
            nbPages: 0,
            zoom: 1,
            index: { scp: {}, fluidra: {} },
            tocPdf: [],
            ligne: null,
            surligne: "",
            recherche: "",
            indexation: null,
            message: "",
            pageSaisie: "",
            largeurFlip: 800,
            compo: "",
            resultats: [],
            recherchant: false,
        });
        this.dernierRendu = "";
        this.tache = null;
        onWillStart(async () => {
            const data = await this.orm.call(MODELE, "pool_catalogue_donnees", [this.resModel, this.resId]);
            this.state.data = data;
            const premiere = data.lignes.find((l) => l.fournisseur);
            if (premiere) {
                this.state.cat = premiere.fournisseur;
            }
            const [scp, fluidra] = await Promise.all([
                this.orm.call(MODELE, "pool_catalogue_index", ["scp"]),
                this.orm.call(MODELE, "pool_catalogue_index", ["fluidra"]),
            ]);
            this.state.index = { scp: scp || {}, fluidra: fluidra || {} };
            this.state.chargement = false;
        });
        onMounted(() => {
            this.ouvrirCatalogue(this.state.cat, true);
        });
        onPatched(() => this.rendreSiBesoin());
        this.surRedim = () => {
            this.dernierRendu = "";
            this.rendreSiBesoin();
        };
        window.addEventListener("resize", this.surRedim);
        onWillUnmount(() => window.removeEventListener("resize", this.surRedim));
    }

    // ------------------------------------------------------------------ affichage
    fmt(v) {
        if (v === null || v === undefined || v === false || v === "") {
            return "—";
        }
        return (
            Number(v).toLocaleString("fr-BE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €"
        );
    }
    get catalogues() {
        return Object.keys(this.state.data.catalogues);
    }
    get conf() {
        return this.state.data.catalogues[this.state.cat];
    }
    get toc() {
        const idx = this.state.index[this.state.cat] || {};
        if (idx.toc && idx.toc.length) {
            return idx.toc;
        }
        return this.state.cat === "scp" ? this.state.tocPdf : [];
    }
    pageAffichee(cat, page) {
        // le flipbook Fluidra numérote ses pages imprimées 2 de moins que ses vues
        return cat === "fluidra" ? Math.max(page - 2, 1) : page;
    }
    chercherIndex(cat, ref) {
        const codes = ((this.state.index[cat] || {}).codes) || {};
        return ref ? codes[norm(ref)] : null;
    }
    get lignes() {
        return this.state.data.lignes.map((l) => {
            const res = Object.assign({}, l);
            const trouve = l.fournisseur ? this.chercherIndex(l.fournisseur, l.ref) : null;
            const indexe = l.fournisseur && (this.state.index[l.fournisseur] || {}).codes;
            res.cat_page = trouve ? trouve[0] : null;
            res.cat_lettre = trouve ? trouve[1] : "";
            res.cat_prix = trouve && trouve[2] !== null && trouve[2] !== undefined ? trouve[2] : null;
            res.cat_page_aff = trouve ? this.pageAffichee(l.fournisseur, trouve[0]) : null;
            if (!l.fournisseur) {
                [res.badge, res.badgeClasse] = ["Fournisseur ?", "text-bg-secondary"];
            } else if (!l.ref) {
                [res.badge, res.badgeClasse] = ["Sans réf.", "text-bg-danger"];
            } else if (!indexe) {
                [res.badge, res.badgeClasse] = ["Non indexé", "text-bg-secondary"];
            } else if (!trouve) {
                [res.badge, res.badgeClasse] = ["Introuvable", "text-bg-warning"];
            } else if (res.cat_prix === null) {
                [res.badge, res.badgeClasse] = ["p." + res.cat_page_aff, "text-bg-info"];
            } else if (Math.abs((l.prix_catalogue || 0) - res.cat_prix) < 0.011) {
                [res.badge, res.badgeClasse] = ["Prix OK", "text-bg-success"];
            } else {
                [res.badge, res.badgeClasse] = ["Prix ≠", "text-bg-warning"];
            }
            return res;
        });
    }
    get baseFlipbook() {
        return (this.state.data.catalogues.fluidra.url || "").replace(/\/?$/, "/");
    }
    get urlFlipbook() {
        return this.baseFlipbook + this.state.page + "/";
    }
    get urlFond() {
        const px = this.state.largeurFlip * (window.devicePixelRatio || 1);
        const taille = px <= 650 ? 1 : px <= 960 ? 2 : px <= 1350 ? 3 : px <= 2050 ? 4 : 5;
        const n = String(this.state.page).padStart(4, "0");
        return this.baseFlipbook + "files/assets/common/page-html5-substrates/page" + n + "_" + taille + ".jpg";
    }
    get urlExterne() {
        if (this.state.cat === "scp") {
            return this.conf.url + "#page=" + this.state.page;
        }
        return this.urlFlipbook;
    }
    get indexInfo() {
        const idx = this.state.index[this.state.cat] || {};
        if (!idx.codes) {
            return "";
        }
        return Object.keys(idx.codes).length + " références indexées le " + (idx.date || "?");
    }

    // ------------------------------------------------------------------ retour et composition
    retour() {
        const fil = (this.env.config && this.env.config.breadcrumbs) || [];
        if (fil.length > 1 && fil[fil.length - 2].onSelected) {
            fil[fil.length - 2].onSelected();
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: this.resModel,
            res_id: this.resId,
            views: [[false, "form"]],
            target: "current",
        });
    }
    trouverAuCatalogue(ref) {
        for (const cat of this.catalogues) {
            const t = this.chercherIndex(cat, ref);
            if (t) {
                return { cat, page: t[0], lettre: t[1], prix: t[2], aff: this.pageAffichee(cat, t[0]) };
            }
        }
        return null;
    }
    libelleCat(cat) {
        return cat === "scp" ? "SCP" : "Fluidra";
    }
    async composer() {
        const lignes = (this.state.compo || "")
            .split(/[\n;]+/)
            .map((l) => l.trim())
            .filter(Boolean);
        if (!lignes.length) {
            return;
        }
        const demandes = lignes.map((l) => {
            const m = l.match(/^(.*?)(?:\s+[xX×]?\s*(\d+(?:[.,]\d+)?))?$/);
            return { terme: (m && m[1] ? m[1] : l).trim(), qte: m && m[2] ? m[2].replace(",", ".") : "1" };
        });
        this.state.recherchant = true;
        try {
            // une référence fabricant connue du catalogue SCP est cherchée sous son code SCP
            const termes = demandes.map((d) => {
                const t = this.chercherIndex("scp", d.terme);
                return t && t[3] ? t[3] : d.terme;
            });
            const res = await this.orm.call(MODELE, "pool_catalogue_chercher", [termes]);
            res.forEach((r, k) => {
                if (termes[k] !== demandes[k].terme) {
                    r.terme = demandes[k].terme + " → " + termes[k];
                }
            });
            this.state.resultats = res.map((r, k) => {
                const auCat = this.trouverAuCatalogue(termes[k]) ||
                    r.produits.map((p) => this.trouverAuCatalogue(p.ref || p.code)).find(Boolean) || null;
                return Object.assign(r, { qte: demandes[k] ? demandes[k].qte : "1", auCat, cle: termes[k] });
            });
            const premier = this.state.resultats.find((r) => r.auCat);
            if (premier) {
                this.montrerCat(premier.auCat, premier.produits[0] ? premier.produits[0].ref || premier.cle : premier.cle);
            }
        } finally {
            this.state.recherchant = false;
        }
    }
    montrerCat(info, ref) {
        if (!info) {
            return;
        }
        if (info.cat !== this.state.cat) {
            this.ouvrirCatalogue(info.cat).then(() => this.allerPage(info.page, ref));
        } else {
            this.allerPage(info.page, ref);
        }
        this.state.message = "";
    }
    montrerProduit(p) {
        const ref = p.ref || p.code;
        const info = this.trouverAuCatalogue(ref);
        if (info) {
            this.montrerCat(info, ref);
        } else {
            this.state.message = "« " + p.nom + " » : référence " + (ref || "inconnue") + " absente des catalogues indexés.";
        }
    }
    rien() {}
    majQte(r, ev) {
        r.qte = ev.target.value;
    }
    infoProduit(p) {
        return this.trouverAuCatalogue(p.ref || p.code);
    }
    async ajouter(p, qte) {
        try {
            this.state.data = await this.orm.call(MODELE, "pool_catalogue_ajouter", [this.resId, p.id, parseFloat(qte) || 1]);
            this.notification.add("« " + p.nom + " » ajouté au devis.", { type: "success" });
        } catch (e) {
            this.notification.add((e.data && e.data.message) || e.message || String(e), { type: "danger" });
        }
    }

    // ------------------------------------------------------------------ navigation
    async ouvrirCatalogue(cat, auto = false) {
        this.state.cat = cat;
        this.state.message = "";
        this.state.surligne = "";
        this.dernierRendu = "";
        if (cat === "scp") {
            try {
                const doc = await this.docScp();
                this.state.nbPages = doc.numPages;
                if (!this.toc.length) {
                    this.state.tocPdf = await this.sommairePdf(doc);
                }
            } catch (e) {
                this.state.message = "Le catalogue SCP n'a pas pu être chargé : " + (e.message || e);
                return;
            }
        } else {
            this.state.nbPages = (this.state.index.fluidra || {}).pages || 586;
        }
        const premiere = auto && this.lignes.find((l) => l.fournisseur === cat && l.cat_page);
        if (premiere) {
            this.selectLigne(premiere);
        } else {
            this.allerPage(cat === "fluidra" ? 5 : 1);
        }
    }
    selectLigne(l) {
        this.state.ligne = l.id;
        if (l.fournisseur && l.fournisseur !== this.state.cat) {
            this.state.cat = l.fournisseur;
            this.ouvrirCatalogue(l.fournisseur).then(() => this.selectLigne(l));
            return;
        }
        if (!l.fournisseur) {
            this.state.message = "Fournisseur inconnu pour « " + l.nom + " » : parcourez les rubriques.";
            return;
        }
        const trouve = this.chercherIndex(l.fournisseur, l.ref);
        if (trouve) {
            this.state.message = "";
            this.allerPage(trouve[0], l.ref);
        } else {
            this.state.message = l.ref
                ? "Référence « " + l.ref + " » absente de l'index du catalogue : parcourez les rubriques ou la recherche."
                : "Cette ligne n'a pas de référence fournisseur.";
        }
    }
    chercher() {
        const ref = (this.state.recherche || "").trim();
        if (!ref) {
            return;
        }
        for (const cat of [this.state.cat, ...this.catalogues.filter((c) => c !== this.state.cat)]) {
            const trouve = this.chercherIndex(cat, ref);
            if (trouve) {
                if (cat !== this.state.cat) {
                    this.ouvrirCatalogue(cat).then(() => this.allerPage(trouve[0], ref));
                } else {
                    this.allerPage(trouve[0], ref);
                }
                this.state.message = "";
                return;
            }
        }
        this.state.message = "« " + ref + " » n'est pas dans les index des catalogues.";
    }
    allerPage(page, surligne = "") {
        page = parseInt(page, 10) || 1;
        if (this.state.nbPages) {
            page = Math.min(Math.max(page, 1), this.state.nbPages);
        }
        this.state.page = page;
        this.state.pageSaisie = String(this.pageAffichee(this.state.cat, page));
        this.state.surligne = surligne;
    }
    pagePrecedente() {
        this.allerPage(this.state.page - 1);
    }
    pageSuivante() {
        this.allerPage(this.state.page + 1);
    }
    saisirPage(ev) {
        const n = parseInt(ev.target.value, 10);
        if (n) {
            this.allerPage(this.state.cat === "fluidra" ? n + 2 : n);
        }
    }
    zoomer(delta) {
        this.state.zoom = Math.min(Math.max(Math.round((this.state.zoom + delta) * 10) / 10, 0.5), 3);
    }

    // ------------------------------------------------------------------ PDF SCP
    async docScp() {
        const url = this.state.data.catalogues.scp.url;
        if (!documentsPdf[url]) {
            documentsPdf[url] = chargerPdfjs().then(
                (L) =>
                    L.getDocument({
                        url,
                        disableAutoFetch: true,
                        disableStream: true,
                        rangeChunkSize: 262144,
                    }).promise
            );
            documentsPdf[url].catch(() => delete documentsPdf[url]);
        }
        return documentsPdf[url];
    }
    async sommairePdf(doc) {
        const sortie = [];
        const parcourir = async (elements, niveau) => {
            for (const el of elements || []) {
                let page = null;
                try {
                    let dest = el.dest;
                    if (typeof dest === "string") {
                        dest = await doc.getDestination(dest);
                    }
                    if (Array.isArray(dest) && dest[0]) {
                        page = (await doc.getPageIndex(dest[0])) + 1;
                    }
                } catch {
                    page = null;
                }
                if (page) {
                    sortie.push({ title: el.title, page, level: niveau });
                }
                if (el.items && el.items.length && niveau < 1) {
                    await parcourir(el.items, niveau + 1);
                }
            }
        };
        await parcourir(await doc.getOutline(), 0);
        return sortie;
    }
    async rendreSiBesoin() {
        if (this.state.chargement || !this.zone.el) {
            return;
        }
        if (this.state.cat === "fluidra") {
            return this.rendreFluidra();
        }
        if (!this.canvas.el) {
            return;
        }
        const cle = [this.state.page, this.state.zoom, this.state.surligne, this.zone.el.clientWidth].join("|");
        if (cle === this.dernierRendu) {
            return;
        }
        this.dernierRendu = cle;
        const L = await chargerPdfjs();
        const doc = await this.docScp();
        const page = await doc.getPage(this.state.page);
        const largeur = Math.max(this.zone.el.clientWidth - 32, 300);
        const echelle = (largeur / page.getViewport({ scale: 1 }).width) * this.state.zoom;
        const vue = page.getViewport({ scale: echelle });
        const ratio = window.devicePixelRatio || 1;
        const toile = this.canvas.el;
        const calque = this.calque.el;
        if (this.state.cat !== "scp" || !toile || !calque) {
            this.dernierRendu = ""; // on a changé de catalogue pendant le chargement
            return;
        }
        for (const c of [toile, calque]) {
            c.width = Math.floor(vue.width * ratio);
            c.height = Math.floor(vue.height * ratio);
            c.style.width = Math.floor(vue.width) + "px";
            c.style.height = Math.floor(vue.height) + "px";
        }
        const ctx = toile.getContext("2d");
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        if (this.tache) {
            this.tache.cancel();
        }
        this.tache = page.render({ canvasContext: ctx, viewport: vue });
        try {
            await this.tache.promise;
        } catch {
            return; // rendu annulé par un rendu plus récent
        }
        if (!calque.isConnected) {
            return;
        }
        const cctx = calque.getContext("2d");
        cctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        cctx.clearRect(0, 0, vue.width, vue.height);
        const cible = norm(this.state.surligne);
        if (cible.length < 3) {
            return;
        }
        const contenu = await page.getTextContent();
        if (!calque.isConnected || !this.zone.el) {
            return;
        }
        let premierY = null;
        cctx.fillStyle = "rgba(255, 200, 0, 0.45)";
        cctx.strokeStyle = "rgba(220, 120, 0, 0.9)";
        cctx.lineWidth = 2;
        for (const it of contenu.items) {
            if (!it.str || !norm(it.str).includes(cible)) {
                continue;
            }
            const t = L.Util.transform(vue.transform, it.transform);
            const h = Math.hypot(t[2], t[3]);
            const x = t[4] - 3;
            const y = t[5] - h - 3;
            const w = it.width * echelle + 6;
            cctx.fillRect(x, y, w, h + 6);
            cctx.strokeRect(x, y, w, h + 6);
            premierY = premierY === null ? y : Math.min(premierY, y);
        }
        if (premierY !== null) {
            this.zone.el.scrollTo({ top: Math.max(premierY - 120, 0), behavior: "smooth" });
        } else {
            this.state.message =
                "Page " + this.state.page + " ouverte, mais la référence n'y est pas lisible : vérifiez à l'œil.";
        }
    }

    async rendreFluidra() {
        if (!this.feuilleFlip.el || !this.calqueSvg.el) {
            return;
        }
        const largeur = Math.round(Math.max(this.zone.el.clientWidth - 32, 300) * this.state.zoom);
        if (largeur !== this.state.largeurFlip) {
            this.state.largeurFlip = largeur; // nouveau rendu après mise à jour
            return;
        }
        const cle = ["f", this.state.page, this.state.surligne, largeur].join("|");
        if (cle === this.dernierRendu) {
            return;
        }
        this.dernierRendu = cle;
        const page = this.state.page;
        const calque = this.calqueSvg.el;
        calque.replaceChildren();
        let svg = "";
        try {
            svg = await this.orm.call(MODELE, "pool_catalogue_fluidra_page", [page]);
        } catch {
            svg = "";
        }
        if (page !== this.state.page || !svg || !calque.isConnected || this.state.cat !== "fluidra") {
            return;
        }
        const doc = new DOMParser().parseFromString(svg, "image/svg+xml");
        const racine = doc.documentElement;
        if (!racine || racine.nodeName.toLowerCase().includes("parsererror")) {
            return;
        }
        const noeud = document.importNode(racine, true);
        noeud.removeAttribute("width");
        noeud.removeAttribute("height");
        noeud.style.width = "100%";
        noeud.style.height = "auto";
        calque.replaceChildren(noeud);
        const cible = norm(this.state.surligne);
        if (cible.length < 3) {
            return;
        }
        const NS = "http://www.w3.org/2000/svg";
        let premier = null;
        for (const t of noeud.getElementsByTagNameNS(NS, "text")) {
            if (!norm(t.textContent).includes(cible)) {
                continue;
            }
            let b;
            try {
                b = t.getBBox();
            } catch {
                continue;
            }
            const r = document.createElementNS(NS, "rect");
            r.setAttribute("x", b.x - 2);
            r.setAttribute("y", b.y - 2);
            r.setAttribute("width", b.width + 4);
            r.setAttribute("height", b.height + 4);
            r.setAttribute("fill", "rgba(255, 200, 0, 0.45)");
            r.setAttribute("stroke", "rgba(220, 120, 0, 0.9)");
            const tr = t.getAttribute("transform");
            if (tr) {
                r.setAttribute("transform", tr);
            }
            t.parentNode.insertBefore(r, t);
            premier = premier || r;
        }
        if (premier) {
            const zr = this.zone.el.getBoundingClientRect();
            const rr = premier.getBoundingClientRect();
            this.zone.el.scrollTo({ top: Math.max(this.zone.el.scrollTop + rr.top - zr.top - 120, 0), behavior: "smooth" });
        } else {
            this.state.message =
                "Page " + this.pageAffichee("fluidra", page) + " ouverte, mais la référence n'y est pas lisible : vérifiez à l'œil.";
        }
    }

    // ------------------------------------------------------------------ index
    async indexerScp() {
        let doc;
        try {
            doc = await this.docScp();
        } catch (e) {
            this.notification.add("Catalogue SCP inaccessible : " + (e.message || e), { type: "danger" });
            return;
        }
        const total = doc.numPages;
        const codes = {};
        const reScp = /[A-Z]{3}-\d{3}-\d{4}/g;
        this.state.indexation = { fait: 0, total };
        for (let p = 1; p <= total; p++) {
            const page = await doc.getPage(p);
            const contenu = await page.getTextContent();
            const texte = contenu.items.map((i) => i.str).join(" ").replace(/\s+/g, " ");
            const positions = [...texte.matchAll(reScp)];
            positions.forEach((m, k) => {
                const fin = k + 1 < positions.length ? positions[k + 1].index : m.index + 220;
                const bloc = texte.slice(m.index + m[0].length, Math.min(fin, m.index + 220));
                const prixM = bloc.match(/\s(A|B|C|D|E|F|P|NET)\s(\d{1,3}(?: \d{3})+,\d{2}|\d+,\d{2})/);
                const lettre = prixM ? prixM[1] : "";
                const prix = prixM ? parseFloat(prixM[2].replace(/ /g, "").replace(",", ".")) : null;
                const cle = norm(m[0]);
                if (!codes[cle] || (codes[cle][2] === null && prix !== null)) {
                    codes[cle] = [p, lettre, prix];
                }
                const fab = (bloc.replace(/^\*/, "").trim().split(" ")[0] || "").replace(/\*$/, "");
                if (fab && fab.length >= 4 && /\d/.test(fab) && !/^\d{1,3}(,\d\d)?$/.test(fab)) {
                    const cf = norm(fab);
                    if (!codes[cf]) {
                        codes[cf] = [p, lettre, prix, m[0]];
                    }
                }
            });
            if (p % 5 === 0 || p === total) {
                this.state.indexation.fait = p;
            }
        }
        const toc = await this.sommairePdf(doc);
        const res = await this.orm.call(MODELE, "pool_catalogue_index_save", ["scp", { codes, toc, pages: total }]);
        this.state.index.scp = await this.orm.call(MODELE, "pool_catalogue_index", ["scp"]);
        this.state.indexation = null;
        this.notification.add(res.codes + " références SCP indexées.", { type: "success" });
    }
    async indexerFluidra() {
        this.state.indexation = { fait: 0, total: 0 };
        try {
            this.state.index.fluidra = await this.orm.call(MODELE, "pool_catalogue_index_fluidra", []);
            this.state.nbPages = this.state.index.fluidra.pages || 0;
            this.notification.add(
                Object.keys(this.state.index.fluidra.codes || {}).length + " références Fluidra indexées.",
                { type: "success" }
            );
        } finally {
            this.state.indexation = null;
        }
    }
    indexer() {
        return this.state.cat === "scp" ? this.indexerScp() : this.indexerFluidra();
    }
}

registry.category("actions").add("lolirine_pool_catalogue", PoolCatalogue);
