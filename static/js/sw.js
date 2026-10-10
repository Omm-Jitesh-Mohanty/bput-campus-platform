/* =========================================================
   Service Worker — Campus Platform
   Strategy:
     - HTML pages: network-first, cache fallback
     - CSS/JS/static: network-first, cache fallback
     - POST requests: queue when offline
   ========================================================= */

const CACHE_NAME = 'campus-v3';
const RUNTIME_CACHE = 'campus-runtime-v3';

const PRECACHE_URLS = [
    '/',
    '/accounts/login/',
    '/static/css/main.css',
    '/static/css/lite.css',
    '/static/css/design-system.css',
    '/static/js/main.js',
    '/static/manifest.json',
];

// -------- Install --------

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(PRECACHE_URLS))
            .catch((err) => console.warn('[SW] Precache failed:', err))
    );

    self.skipWaiting();
});

// -------- Activate --------

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter(
                        (key) =>
                            key !== CACHE_NAME &&
                            key !== RUNTIME_CACHE
                    )
                    .map((key) => caches.delete(key))
            )
        )
    );

    self.clients.claim();
});

// -------- Fetch --------

self.addEventListener('fetch', (event) => {
    const req = event.request;

    if (
        req.method !== 'GET' &&
        req.method !== 'POST'
    ) {
        return;
    }

    if (
        req.url.includes('/admin/') ||
        req.url.includes('/i18n/')
    ) {
        return;
    }

    // -------- POST --------

    if (req.method === 'POST') {
        event.respondWith(
            handlePostRequest(req)
        );
        return;
    }

    const url = new URL(req.url);

    // -------- HTML navigation --------

    if (req.mode === 'navigate') {
        event.respondWith(
            networkFirst(
                req,
                CACHE_NAME
            )
        );
        return;
    }

    // -------- CSS / JavaScript --------

    if (
        url.pathname.endsWith('.css') ||
        url.pathname.endsWith('.js')
    ) {
        event.respondWith(
            networkFirst(
                req,
                RUNTIME_CACHE
            )
        );
        return;
    }

    // -------- Images / fonts / other static --------

    event.respondWith(
        networkFirst(
            req,
            RUNTIME_CACHE
        )
    );
});

// =========================================================
// Helpers
// =========================================================

async function networkFirst(req, cacheName) {
    try {
        /*
         * Force a fresh network request while online.
         * This prevents the browser's HTTP cache from
         * defeating the network-first strategy.
         */
        const freshRequest = new Request(req, {
            cache: 'no-store',
        });

        const response = await fetch(freshRequest);

        if (response && response.status === 200) {
            const cache = await caches.open(cacheName);
            await cache.put(req, response.clone());
        }

        return response;
    } catch (err) {
        const cached = await caches.match(req);

        if (cached) {
            return cached;
        }

        if (req.mode === 'navigate') {
            const fallback = await caches.match('/');

            if (fallback) {
                return fallback;
            }
        }

        return new Response(
            '<h1>You are offline</h1><p>Please reconnect to continue.</p>',
            {
                status: 503,
                headers: {
                    'Content-Type': 'text/html',
                },
            }
        );
    }
}

// -------- POST handling --------

async function handlePostRequest(req) {
    try {
        const response = await fetch(req.clone());
        return response;
    } catch (err) {
        const cloned = req.clone();
        const body = await cloned.text();
        const url = new URL(cloned.url);

        const allClients = await self.clients.matchAll({
            type: 'window',
        });

        allClients.forEach((client) => {
            client.postMessage({
                type: 'QUEUE_POST',
                url: url.pathname,
                body: body,
                headers: Object.fromEntries(
                    cloned.headers.entries()
                ),
            });
        });

        return new Response(
            JSON.stringify({
                queued: true,
                message: 'Request queued. Will sync when online.',
            }),
            {
                status: 202,
                headers: {
                    'Content-Type': 'application/json',
                },
            }
        );
    }
}

// -------- Sync on reconnect --------
self.addEventListener('message', (event) => {
    if (
        event.data &&
        event.data.type === 'SKIP_WAITING'
    ) {
        self.skipWaiting();
        return;
    }

    if (
        event.data &&
        event.data.type === 'SYNC_NOW'
    ) {
        self.clients
            .matchAll()
            .then((clients) => {
                clients.forEach((client) => {
                    client.postMessage({
                        type: 'SYNC_TRIGGERED',
                    });
                });
            });
    }
});