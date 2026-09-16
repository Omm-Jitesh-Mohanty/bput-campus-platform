/* =========================================================
   Service Worker — Campus Platform
   Strategy:
     - HTML pages:  network-first, cache fallback
     - Static:      cache-first
     - POST /tickets/submit/:  queue when offline, sync later
   ========================================================= */

const CACHE_NAME = 'campus-v2';
const RUNTIME_CACHE = 'campus-runtime-v2';

const PRECACHE_URLS = [
    '/',
    '/accounts/login/',
    '/static/css/main.css',
    '/static/css/lite.css',
    '/static/js/main.js',
    '/static/manifest.json',
];

// -------- Install --------
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
            .catch((err) => console.warn('Precache failed:', err))
    );
    self.skipWaiting();
});

// -------- Activate --------
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((k) => k !== CACHE_NAME && k !== RUNTIME_CACHE)
                    .map((k) => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

// -------- Fetch --------
self.addEventListener('fetch', (event) => {
    const req = event.request;

    // Skip non-GET/POST
    if (req.method !== 'GET' && req.method !== 'POST') return;

    // Skip admin URLs
    if (req.url.includes('/admin/') || req.url.includes('/i18n/')) return;

    // ---- POST: queue if network fails ----
    if (req.method === 'POST') {
        event.respondWith(handlePostRequest(req));
        return;
    }

    // ---- GET: network-first for HTML, cache-first for static ----
    if (req.mode === 'navigate') {
        event.respondWith(networkFirst(req, CACHE_NAME));
        return;
    }

    event.respondWith(cacheFirst(req, RUNTIME_CACHE));
});

// =========================================================
// Helpers
// =========================================================

async function networkFirst(req, cacheName) {
    try {
        const res = await fetch(req);
        if (res && res.status === 200) {
            const cache = await caches.open(cacheName);
            cache.put(req, res.clone());
        }
        return res;
    } catch (err) {
        const cached = await caches.match(req);
        if (cached) return cached;

        // Offline fallback: serve cached homepage if requested page not cached
        const fallback = await caches.match('/');
        if (fallback) return fallback;

        return new Response(
            '<h1>You are offline</h1><p>Please reconnect to continue.</p>',
            { headers: { 'Content-Type': 'text/html' } }
        );
    }
}

async function cacheFirst(req, cacheName) {
    const cached = await caches.match(req);
    if (cached) return cached;

    try {
        const res = await fetch(req);
        if (res && res.status === 200) {
            const cache = await caches.open(cacheName);
            cache.put(req, res.clone());
        }
        return res;
    } catch (err) {
        return new Response('', { status: 503 });
    }
}

async function handlePostRequest(req) {
    try {
        const res = await fetch(req.clone());
        return res;
    } catch (err) {
        // ---- Network failed: queue for sync ----
        const cloned = req.clone();
        const body = await cloned.text();
        const url = new URL(cloned.url);

        // Save to IndexedDB via broadcast to open pages
        const allClients = await self.clients.matchAll({ type: 'window' });
        allClients.forEach((client) => {
            client.postMessage({
                type: 'QUEUE_POST',
                url: url.pathname,
                body: body,
                headers: Object.fromEntries(cloned.headers.entries()),
            });
        });

        // Return a synthetic "queued" response
        return new Response(
            JSON.stringify({
                queued: true,
                message: 'Request queued. Will sync when online.',
            }),
            { status: 202, headers: { 'Content-Type': 'application/json' } }
        );
    }
}

// -------- Sync on reconnect --------
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SYNC_NOW') {
        // Client-side handles actual sync; SW just triggers
        self.clients.matchAll().then((clients) => {
            clients.forEach((c) => c.postMessage({ type: 'SYNC_TRIGGERED' }));
        });
    }
});