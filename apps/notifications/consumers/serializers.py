"""Notification serialization for WebSocket payloads."""
from apps.core.templatetags.campus_extras import short_time_ago


def serialize_notification(n):
    return {
        'id': n.id,
        'event_code': n.event_code,
        'title': n.title,
        'body': n.body,
        'icon': n.icon,
        'priority': n.priority,
        'link_url': n.link_url,
        'is_read': n.is_read,
        'time_ago': short_time_ago(n.created_at),
        'created_at': n.created_at.isoformat(),
    }