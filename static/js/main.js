/* =========================================================
   Main JavaScript — Campus Platform
   - Service worker registration
   - Automatic service worker update
   - Online/offline detection
   - IndexedDB queue for offline submissions
   - Auto-sync on reconnect
   ========================================================= */

// ============= Service Worker Registration =============

if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            const registration =
                await navigator.serviceWorker.register(
                    '/sw.js',
                    {
                        scope: '/',
                    }
                );

            console.log(
                '[SW] registered:',
                registration.scope
            );

            await registration.update();

            if (registration.waiting) {
                registration.waiting.postMessage({
                    type: 'SKIP_WAITING',
                });
            }

        } catch (err) {
            console.warn(
                '[SW] registration failed:',
                err
            );
        }
    });

    navigator.serviceWorker.addEventListener(
        'message',
        (event) => {
            if (
                event.data &&
                event.data.type === 'QUEUE_POST'
            ) {
                queuePost(
                    event.data.url,
                    event.data.body,
                    event.data.headers
                );
            }
        }
    );

    let refreshing = false;

    navigator.serviceWorker.addEventListener(
        'controllerchange',
        () => {
            if (refreshing) {
                return;
            }

            refreshing = true;

            console.log(
                '[SW] New service worker activated.'
            );

            window.location.reload();
        }
    );
}

// ============= Online / Offline detection =============

window.addEventListener('offline', () => {
    showBanner(
        '📴 You are offline. Your submissions will be saved and synced.',
        'warning'
    );
});

window.addEventListener('online', () => {
    showBanner(
        '🌐 Back online. Syncing…',
        'success'
    );

    syncQueue();
});

// ============= Banner helper =============

function showBanner(text, type = 'info') {
    let banner =
        document.getElementById('net-banner');

    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'net-banner';

        banner.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            padding: 12px;
            text-align: center;
            font-weight: 600;
            z-index: 9999;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        `;

        document.body.prepend(banner);
    }

    banner.textContent = text;

    banner.style.background =
        type === 'warning'
            ? '#f59e0b'
            : type === 'success'
                ? '#16a34a'
                : type === 'error'
                    ? '#dc2626'
                    : '#1e40af';

    banner.style.color = 'white';

    if (type === 'success') {
        setTimeout(() => {
            if (banner) {
                banner.remove();
            }
        }, 3000);
    }
}

// ============= IndexedDB Queue =============

const DB_NAME = 'campus_offline';
const STORE = 'queue';
const DB_VERSION = 1;

function openDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(
            DB_NAME,
            DB_VERSION
        );

        req.onupgradeneeded = (event) => {
            const db = event.target.result;

            if (!db.objectStoreNames.contains(STORE)) {
                db.createObjectStore(
                    STORE,
                    {
                        keyPath: 'id',
                        autoIncrement: true,
                    }
                );
            }
        };

        req.onsuccess = () => {
            resolve(req.result);
        };

        req.onerror = () => {
            reject(req.error);
        };
    });
}

async function queuePost(
    url,
    body,
    headers
) {
    try {
        const db = await openDB();

        const tx = db.transaction(
            STORE,
            'readwrite'
        );

        tx.objectStore(STORE).add({
            url,
            body,
            headers: headers || {},
            timestamp: Date.now(),
        });

        await new Promise(
            (resolve) => {
                tx.oncomplete = resolve;
            }
        );

        showBanner(
            '📥 Saved offline. Will sync when online.',
            'warning'
        );

    } catch (err) {
        console.error(
            '[Queue] Failed:',
            err
        );

        showBanner(
            '❌ Failed to save offline. Please try again.',
            'error'
        );
    }
}

async function getQueue() {
    const db = await openDB();

    const tx = db.transaction(
        STORE,
        'readonly'
    );

    const req =
        tx.objectStore(STORE).getAll();

    return new Promise((resolve) => {
        req.onsuccess = () => {
            resolve(req.result || []);
        };
    });
}

async function removeFromQueue(ids) {
    const db = await openDB();

    const tx = db.transaction(
        STORE,
        'readwrite'
    );

    const store =
        tx.objectStore(STORE);

    ids.forEach((id) => {
        store.delete(id);
    });

    return new Promise(
        (resolve) => {
            tx.oncomplete = resolve;
        }
    );
}

async function syncQueue() {
    if (!navigator.onLine) {
        return;
    }

    const items = await getQueue();

    if (items.length === 0) {
        return;
    }

    console.log(
        `[Sync] Pushing ${items.length} queued item(s)…`
    );

    const succeededIds = [];

    for (const item of items) {
        try {
            const response = await fetch(
                item.url,
                {
                    method: 'POST',
                    headers: {
                        ...item.headers,
                        'X-CSRFToken': getCSRF(),
                    },
                    body: item.body,
                }
            );

            if (
                response.ok ||
                response.status === 302
            ) {
                succeededIds.push(item.id);

            } else {
                console.warn(
                    '[Sync] Server rejected:',
                    response.status,
                    item.url
                );
            }

        } catch (err) {
            console.warn(
                '[Sync] Failed item:',
                item.url,
                err
            );

            break;
        }
    }

    if (succeededIds.length) {
        await removeFromQueue(
            succeededIds
        );

        showBanner(
            `✅ Synced ${succeededIds.length} item(s).`,
            'success'
        );

        setTimeout(() => {
            window.location.reload();
        }, 1200);
    }
}

function getCSRF() {
    const match =
        document.cookie.match(
            /csrftoken=([^;]+)/
        );

    return match
        ? match[1]
        : '';
}

// ============= Auto-sync on page load =============

document.addEventListener(
    'DOMContentLoaded',
    () => {
        if (navigator.onLine) {
            syncQueue().catch(
                (err) => {
                    console.warn(
                        '[Sync] init failed:',
                        err
                    );
                }
            );
        }
    }
);