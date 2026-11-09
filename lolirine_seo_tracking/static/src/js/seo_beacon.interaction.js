/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/*
 * Balise de mesure d'audience SEO (sans cookie, sans identifiant).
 *
 * - Une page vue = un envoi navigator.sendBeacon vers /lolirine_seo/hit.
 * - La 1re page d'une visite (arrivée depuis un autre site, ou nouvel onglet)
 *   est marquée « entrée » ; son référent + son URL (utm, gclid...) sont gardés
 *   en sessionStorage et renvoyés avec chaque page vue, pour attribuer une
 *   commande confirmée à la source de la visite.
 * - Rien n'est envoyé dans l'éditeur, dans une iframe ou par un navigateur piloté.
 * - Le serveur ignore les sites non suivis et les robots.
 */
const ENTRY_KEY = "lolirine_seo_entry";

function readEntry() {
    try {
        return JSON.parse(window.sessionStorage.getItem(ENTRY_KEY) || "null");
    } catch {
        return null;
    }
}

function writeEntry(entry) {
    try {
        window.sessionStorage.setItem(ENTRY_KEY, JSON.stringify(entry));
    } catch {
        // stockage indisponible (navigation privée stricte) : on continue sans
    }
}

function refHost(ref) {
    try {
        return ref ? new URL(ref).host : "";
    } catch {
        return "";
    }
}

export class LolirineSeoBeacon extends Interaction {
    static selector = "#wrapwrap";

    start() {
        if (window.__lolirineSeoSent) {
            return;
        }
        window.__lolirineSeoSent = true;
        try {
            if (window.self !== window.top || navigator.webdriver) {
                return;
            }
            const params = new URLSearchParams(window.location.search);
            if (params.has("enable_editor") || params.has("edit_translations") ||
                document.body.classList.contains("editor_enable")) {
                return;
            }
            const ref = document.referrer || "";
            const external = ref && refHost(ref) !== window.location.host;
            let entry = readEntry();
            let landing = false;
            if (!entry || external) {
                entry = { er: ref, eu: window.location.href.slice(0, 1500) };
                writeEntry(entry);
                landing = true;
            }
            const payload = JSON.stringify({
                p: window.location.pathname,
                l: landing ? 1 : 0,
                er: (entry.er || "").slice(0, 1000),
                eu: entry.eu || "",
                lg: document.documentElement.lang || "",
            });
            const url = "/lolirine_seo/hit";
            const blob = new Blob([payload], { type: "text/plain" });
            if (!(navigator.sendBeacon && navigator.sendBeacon(url, blob))) {
                fetch(url, { method: "POST", body: payload, keepalive: true,
                    credentials: "same-origin" }).catch(() => {});
            }
        } catch {
            // la mesure ne doit jamais gêner la page
        }
    }
}

registry
    .category("public.interactions")
    .add("lolirine_seo_tracking.seo_beacon", LolirineSeoBeacon);
