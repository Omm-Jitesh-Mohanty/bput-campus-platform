/* =========================================================
   WebSocket client for the Campus Platform.

   Usage:
     const client = new CampusWS('/ws/notifications/');
     client.on('notification_push', (data) => { ... });
     client.connect();

   Auto-reconnect with exponential backoff.
   Falls back to polling after repeated WebSocket failures.
   ========================================================= */

class CampusWS {
    constructor(path) {
        this.path = path;
        this.handlers = {};
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 30000;   // 30s
        this.shouldReconnect = true;
    }

    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}${this.path}`;

        try {
            this.ws = new WebSocket(url);
        } catch (e) {
            console.error('[WS] Failed to construct:', e);
            this.scheduleReconnect();
            return;
        }

        this.ws.onopen = () => {
            console.log('[WS] Connected:', this.path);
            this.reconnectAttempts = 0;
            this.emit('open', {});
        };

        this.ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                this.emit(data.type, data);
                this.emit('*', data);
            } catch (err) {
                console.warn('[WS] Bad message:', e.data);
            }
        };

        this.ws.onclose = (e) => {
            console.log('[WS] Closed:', this.path, 'code=', e.code);
            this.emit('close', { code: e.code });

            if (
                this.shouldReconnect &&
                e.code !== 4001 &&
                e.code !== 4003
            ) {
                this.scheduleReconnect();
            }
        };

        this.ws.onerror = (e) => {
            console.warn('[WS] Error:', e);
        };

        // Heartbeat
        this.startHeartbeat();
    }

    scheduleReconnect() {
        this.reconnectAttempts++;

        if (
            this.reconnectAttempts > 3 &&
            !this._fallbackStarted
        ) {
            this._fallbackStarted = true;

            console.warn('[WS] Falling back to polling');

            this.startFallbackPolling();
        }

        const delay = Math.min(
            1000 * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );

        setTimeout(() => this.connect(), delay);
    }

    startFallbackPolling() {
        if (this._pollInterval) return;

        this._pollInterval = setInterval(() => {
            fetch('/notifications/unread-count.json', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(r => r.json())
                .then(data => this.emit('unread_count', data));
        }, 30000);   // 30s fallback
    }

    startHeartbeat() {
        if (this._heartbeatInterval) {
            clearInterval(this._heartbeatInterval);
        }

        this._heartbeatInterval = setInterval(() => {
            if (
                this.ws &&
                this.ws.readyState === WebSocket.OPEN
            ) {
                this.send({
                    type: 'ping'
                });
            }
        }, 25000);
    }

    send(data) {
        if (
            this.ws &&
            this.ws.readyState === WebSocket.OPEN
        ) {
            this.ws.send(JSON.stringify(data));
        }
    }

    on(type, handler) {
        if (!this.handlers[type]) {
            this.handlers[type] = [];
        }

        this.handlers[type].push(handler);
    }

    emit(type, data) {
        (this.handlers[type] || []).forEach(h => {
            try {
                h(data);
            } catch (e) {
                console.error(
                    '[WS] Handler error:',
                    e
                );
            }
        });
    }

    close() {
        this.shouldReconnect = false;

        if (this.ws) {
            this.ws.close();
        }
    }
}

// Expose globally
window.CampusWS = CampusWS;