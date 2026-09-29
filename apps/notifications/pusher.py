"""
Push notifications to connected WebSocket clients.

Uses Django Channels' channel layer. Since channel_layer is async,
we bridge sync → async via asgiref.sync.async_to_sync.

Safe: if Redis is down, logs a warning but never crashes the caller.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def push_to_user(user_id: int, event_type: str, payload: dict):
    """
    Send a message to a specific user's WebSocket group.

    event_type: e.g., 'notification.push', 'unread_count_update'
    payload: dict to send
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    group = f'user_{user_id}'

    try:
        async_to_sync(channel_layer.group_send)(group, {
            'type': event_type,
            **payload,
        })
    except Exception as e:
        logger.warning(f'push_to_user failed for user {user_id}: {e}')


def push_notification(notification):
    """Push a Notification object to its recipient."""
    from .consumers.serializers import serialize_notification

    user_id = notification.recipient_id

    # Push the notification itself
    push_to_user(user_id, 'notification.push', {
        'notification': serialize_notification(notification),
    })

    # Also push updated unread count
    count = notification.recipient.notifications.filter(is_read=False).count()
    push_to_user(user_id, 'unread_count_update', {'count': count})