"""
Base WebSocket consumer with common helpers.

All our consumers extend this to get:
  - Automatic user group join on connect
  - Heartbeat handling
  - Safe JSON serialization
  - Logging
"""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class BaseUserConsumer(AsyncWebsocketConsumer):
    """
    Base for all user-scoped consumers.
    Auto-joins the user's personal group: `user_<id>`.
    """

    async def connect(self):
        user = self.scope.get('user')

        if not user or not user.is_authenticated:
            logger.warning('WS connect rejected: unauthenticated')
            await self.close(code=4001)
            return

        self.user = user
        self.user_group = f'user_{user.id}'

        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )

        await self._update_presence(online=True)

        await self.accept()

        logger.info(
            f'WS connected: user={user.username} '
            f'consumer={self.__class__.__name__}'
        )

        # Send initial payload
        await self.send_json({
            'type': 'connected',
            'user_id': user.id,
            'username': user.username,
            'consumer': self.__class__.__name__,
        })

    async def disconnect(self, code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )

        await self._update_presence(online=False)

        logger.info(f'WS disconnected: code={code}')

    async def _update_presence(self, online: bool):
        from django.core.cache import cache

        key = f'presence_user_{self.user.id}'

        try:
            if online:
                cache.set(key, True, timeout=300)
            else:
                cache.delete(key)
        except Exception as e:
            logger.warning(f'presence update failed: {e}')

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming messages from the client."""
        try:
            data = json.loads(text_data or '{}')
        except json.JSONDecodeError:
            return

        msg_type = data.get('type', '')

        if msg_type == 'ping':
            await self.send_json({'type': 'pong'})
        elif msg_type == 'mark_read':
            await self.handle_mark_read(data)
        else:
            await self.handle_message(data)

    async def handle_message(self, data):
        """Override in subclasses."""
        pass

    async def handle_mark_read(self, data):
        """Override in subclasses."""
        pass

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))

    # -------- Group event handlers (called from channel_layer.group_send) --------

    async def notify_message(self, event):
        """
        Handler for messages of type `notify.message`.
        Called when a group sends to this consumer.
        """
        await self.send_json({
            'type': 'notification',
            'payload': event.get('payload', {}),
        })

    async def notification_push(self, event):
        """
        Handler for messages of type `notification.push`.
        """
        await self.send_json({
            'type': 'notification_push',
            'notification': event.get('notification', {}),
        })

    async def unread_count_update(self, event):
        await self.send_json({
            'type': 'unread_count',
            'count': event.get('count', 0),
        })