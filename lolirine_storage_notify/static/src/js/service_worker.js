/**
 * Lolirine Storage Notify – Service Worker
 * Gère les Web Push Notifications au niveau OS,
 * même quand le navigateur est fermé ou en arrière-plan.
 *
 * Servi via /sw-lolirine.js (controller Python)
 */

'use strict';

const SW_VERSION = '1.0.0';
const CACHE_NAME = `lolirine-notify-v${SW_VERSION}`;

// ─────────────────────────────────────────────────────────
//  Install & Activate
// ─────────────────────────────────────────────────────────

self.addEventListener('install', (event) => {
    console.log('[SW Lolirine] Installé v' + SW_VERSION);
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[SW Lolirine] Activé');
    event.waitUntil(self.clients.claim());
});

// ─────────────────────────────────────────────────────────
//  Push Event – Affichage de la notification OS
// ─────────────────────────────────────────────────────────

self.addEventListener('push', (event) => {
    let data = {};
    try {
        data = event.data ? event.data.json() : {};
    } catch (e) {
        console.error('[SW Lolirine] Erreur parsing push:', e);
        data = { title: 'Lolirine', body: event.data ? event.data.text() : '' };
    }

    const title   = data.title  || '🔔 Lolirine Garde-Meuble';
    const options = {
        body:              data.body    || data.message || '',
        icon:              data.icon    || '/web/static/img/favicon.ico',
        badge:             data.badge   || '/web/static/img/favicon.ico',
        tag:               data.tag     || 'lolirine-notify',
        data:              { url: data.url || '/odoo' },
        requireInteraction: data.requireInteraction || false,
        vibrate:           [200, 100, 200],
        actions: [
            { action: 'open',    title: '👁️ Voir'       },
            { action: 'dismiss', title: '✖ Ignorer'    },
        ],
        // Style visuel de la notif
        silent: false,
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

// ─────────────────────────────────────────────────────────
//  Notification Click – Ouverture de l'URL
// ─────────────────────────────────────────────────────────

self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'dismiss') return;

    const targetUrl = (event.notification.data && event.notification.data.url)
        ? event.notification.data.url
        : '/odoo';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            // Chercher un onglet déjà ouvert sur le même domaine
            for (const client of clientList) {
                if (client.url.includes('/odoo') && 'focus' in client) {
                    client.focus();
                    client.navigate(targetUrl);
                    return;
                }
            }
            // Sinon ouvrir un nouvel onglet
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});

// ─────────────────────────────────────────────────────────
//  Push Subscription Change
// ─────────────────────────────────────────────────────────

self.addEventListener('pushsubscriptionchange', (event) => {
    console.log('[SW Lolirine] Abonnement push changé, re-souscription...');
    // Le JS principal se charge de re-souscrire via push_register_backend.js
    event.waitUntil(
        self.clients.matchAll({ type: 'window' }).then((clients) => {
            clients.forEach(client => client.postMessage({ type: 'PUSH_SUBSCRIPTION_CHANGED' }));
        })
    );
});
