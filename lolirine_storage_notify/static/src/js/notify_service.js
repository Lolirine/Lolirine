/** @odoo-module **/

/**
 * Lolirine Storage Notify – Service OWL Backend
 *
 * S'enregistre au démarrage du backend Odoo et :
 *   1. Écoute le canal bus 'lolirine_notify' → affiche des toasts
 *   2. Enregistre le Service Worker pour les Web Push
 *   3. Re-souscrit si l'abonnement push a changé
 */

import { registry }        from "@web/core/registry";
import { browser }         from "@web/core/browser/browser";

// ─────────────────────────────────────────────────────────
//  Utilitaire : convertir une base64 URL-safe en Uint8Array
// ─────────────────────────────────────────────────────────
function urlBase64ToUint8Array(base64String) {
    const padding   = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64    = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData   = atob(base64);
    const outputArr = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArr[i] = rawData.charCodeAt(i);
    }
    return outputArr;
}

// ─────────────────────────────────────────────────────────
//  Service Lolirine Notify
// ─────────────────────────────────────────────────────────
const lolirineNotifyService = {
    dependencies: ["bus_service", "notification", "rpc", "user"],

    async start(env, { bus_service, notification, rpc, user }) {

        // ── 1. Écoute du bus Odoo ────────────────────────
        bus_service.subscribe("lolirine_notify", (payload) => {
            if (!payload) return;

            const type    = payload.type    || "info";   // info | success | warning | danger
            const title   = payload.title   || "🔔 Lolirine";
            const message = payload.message || "";
            const url     = payload.url     || null;

            notification.add(message, {
                title,
                type,
                sticky: false,
                buttons: url
                    ? [{
                        name: "Voir",
                        onClick: () => { browser.location.href = url; },
                        primary: true,
                    }]
                    : [],
            });
        });

        bus_service.start();

        // ── 2. Web Push – Enregistrement du Service Worker ─
        if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
            console.log("[Lolirine Notify] Web Push non supporté sur ce navigateur.");
            return;
        }

        // Récupérer la clé VAPID publique
        let vapidPublicKey = "";
        try {
            const resp = await fetch("/lolirine/notify/vapid-public-key", {
                headers: { "Accept": "application/json" }
            });
            if (resp.ok) {
                const data = await resp.json();
                vapidPublicKey = data.publicKey || "";
            }
        } catch (e) {
            console.warn("[Lolirine Notify] Impossible de récupérer la clé VAPID:", e);
        }

        if (!vapidPublicKey) {
            console.log("[Lolirine Notify] Clé VAPID non configurée – Web Push désactivé.");
            return;
        }

        // Enregistrer le Service Worker
        let swRegistration = null;
        try {
            swRegistration = await navigator.serviceWorker.register("/sw-lolirine.js", {
                scope: "/",
                updateViaCache: "none",
            });
            console.log("[Lolirine Notify] Service Worker enregistré ✓");
        } catch (e) {
            console.error("[Lolirine Notify] Échec enregistrement SW:", e);
            return;
        }

        // Écouter les changements d'abonnement depuis le SW
        navigator.serviceWorker.addEventListener("message", async (event) => {
            if (event.data && event.data.type === "PUSH_SUBSCRIPTION_CHANGED") {
                await subscribeUser(swRegistration, vapidPublicKey, rpc);
            }
        });

        // Souscrire si pas encore abonné
        await subscribeUser(swRegistration, vapidPublicKey, rpc);
    },
};


// ─────────────────────────────────────────────────────────
//  Logique de souscription push
// ─────────────────────────────────────────────────────────
async function subscribeUser(swRegistration, vapidPublicKey, rpc) {
    // Vérifier la permission
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
        console.log("[Lolirine Notify] Permission refusée pour les notifications.");
        return;
    }

    try {
        // Vérifier l'abonnement existant
        let subscription = await swRegistration.pushManager.getSubscription();

        if (subscription) {
            // Vérifier si déjà enregistré côté serveur
            const status = await rpc("/lolirine/notify/status", {
                endpoint: subscription.endpoint,
            });
            if (status && status.subscribed) {
                console.log("[Lolirine Notify] Abonnement push déjà actif ✓");
                return;
            }
            // Abonnement existant mais non enregistré → ré-enregistrer
        } else {
            // Créer un nouvel abonnement
            const applicationServerKey = urlBase64ToUint8Array(vapidPublicKey);
            subscription = await swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey,
            });
        }

        // Envoyer l'abonnement au serveur
        const subJson = subscription.toJSON();
        await rpc("/lolirine/notify/subscribe", {
            endpoint:   subJson.endpoint,
            p256dh:     subJson.keys.p256dh,
            auth:       subJson.keys.auth,
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
