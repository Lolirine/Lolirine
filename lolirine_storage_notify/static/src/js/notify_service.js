/** @odoo-module **/

/**
 * Lolirine Storage Notify – Service OWL Backend (Odoo 19)
 *
 * Dépendances uniquement sur bus_service et notification,
 * qui existent dans toutes les versions récentes.
 * Les appels RPC utilisent fetch() natif pour éviter les
 * dépendances fragiles au service 'rpc' / 'user'.
 */

import { registry } from "@web/core/registry";
import { browser }  from "@web/core/browser/browser";

// ─────────────────────────────────────────────────────────
//  Utilitaire VAPID
// ─────────────────────────────────────────────────────────
function urlBase64ToUint8Array(base64String) {
    const padding   = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64    = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData   = atob(base64);
    const out       = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; i++) out[i] = rawData.charCodeAt(i);
    return out;
}

// ─────────────────────────────────────────────────────────
//  Helper fetch JSON (remplace le service rpc)
// ─────────────────────────────────────────────────────────
async function jsonRpc(route, params = {}) {
    const res = await fetch(route, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ jsonrpc: '2.0', method: 'call', params }),
    });
    const data = await res.json();
    return data.result;
}

// ─────────────────────────────────────────────────────────
//  Service Lolirine Notify
// ─────────────────────────────────────────────────────────
const lolirineNotifyService = {
    // Uniquement des dépendances stables en Odoo 19
    dependencies: ["bus_service", "notification"],

    async start(env, { bus_service, notification }) {

        // ── 1. Écoute bus Odoo (toast) ───────────────────
        bus_service.subscribe("lolirine_notify", (payload) => {
            if (!payload) return;
            const type    = payload.type    || "info";
            const title   = payload.title   || "🔔 Lolirine";
            const message = payload.message || "";
            const url     = payload.url     || null;

            notification.add(message, {
                title,
                type,
                sticky: true,   // Reste affiché jusqu'au clic
                buttons: url ? [{
                    name: "👁 Voir",
                    onClick: () => { browser.location.href = url; },
                    primary: true,
                }] : [],
            });
        });

        bus_service.start();

        // ── 2. Web Push ──────────────────────────────────
        if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
            console.log("[Lolirine Notify] Web Push non supporté.");
            return;
        }

        // Récupérer la clé VAPID publique via GET simple
        let vapidPublicKey = "";
        try {
            const resp = await fetch("/lolirine/notify/vapid-public-key");
            if (resp.ok) {
                const data = await resp.json();
                vapidPublicKey = data.publicKey || "";
            }
        } catch (e) {
            console.warn("[Lolirine Notify] Clé VAPID non disponible:", e);
        }

        if (!vapidPublicKey) {
            console.log("[Lolirine Notify] Clé VAPID non configurée – Web Push désactivé.");
            return;
        }

        // Enregistrer le Service Worker
        let swReg = null;
        try {
            swReg = await navigator.serviceWorker.register("/sw-lolirine.js", {
                scope: "/",
                updateViaCache: "none",
            });
            console.log("[Lolirine Notify] Service Worker enregistré ✓");
        } catch (e) {
            console.error("[Lolirine Notify] Échec SW:", e);
            return;
        }

        // Re-souscrire si le SW signale un changement
        navigator.serviceWorker.addEventListener("message", async (event) => {
            if (event.data?.type === "PUSH_SUBSCRIPTION_CHANGED") {
                await _subscribePush(swReg, vapidPublicKey);
            }
        });

        // Tentative automatique (Chrome/Firefox)
        // Safari nécessite un geste utilisateur → géré par le bouton dans l'UI
        if (!navigator.userAgent.includes('Safari') || navigator.userAgent.includes('Chrome')) {
            await _subscribePush(swReg, vapidPublicKey);
        }

        // Écouter le clic du bouton "Activer les notifications"
        document.addEventListener('lolirine_request_push_permission', async () => {
            await _subscribePush(swReg, vapidPublicKey);
        });
    },
};


// ─────────────────────────────────────────────────────────
//  Logique de souscription push (utilise fetch/jsonRpc)
// ─────────────────────────────────────────────────────────
async function _subscribePush(swReg, vapidPublicKey) {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
        console.log("[Lolirine Notify] Permission notifications refusée.");
        return;
    }

    try {
        let subscription = await swReg.pushManager.getSubscription();

        if (subscription) {
            // Vérifier si déjà connu côté serveur
            const status = await jsonRpc("/lolirine/notify/status", {
                endpoint: subscription.endpoint,
            });
            if (status?.subscribed) {
                console.log("[Lolirine Notify] Abonnement push déjà actif ✓");
                return;
            }
        } else {
            subscription = await swReg.pushManager.subscribe({
                userVisibleOnly:      true,
                applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
            });
        }

        const sub = subscription.toJSON();
        await jsonRpc("/lolirine/notify/subscribe", {
            endpoint:   sub.endpoint,
            p256dh:     sub.keys.p256dh,
            auth:       sub.keys.auth,
            user_agent: navigator.userAgent.substring(0, 200),
        });

        console.log("[Lolirine Notify] Abonnement push enregistré ✓");
    } catch (e) {
        console.error("[Lolirine Notify] Erreur souscription push:", e);
    }
}


// ─────────────────────────────────────────────────────────
//  Enregistrement du service
// ─────────────────────────────────────────────────────────
registry.category("services").add("lolirine_notify_service", lolirineNotifyService);
