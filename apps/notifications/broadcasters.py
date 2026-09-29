"""
Broadcast ticket and notice events to connected clients.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .consumers.ticket_serializers import serialize_ticket_summary

logger = logging.getLogger(__name__)


def broadcast_ticket_created(ticket):
    """Notify all connected admins of a new ticket."""
    _broadcast_to_admins('ticket_created', {
        'ticket': serialize_ticket_summary(ticket),
    })


def broadcast_ticket_updated(ticket):
    _broadcast_to_admins('ticket_updated', {
        'ticket': serialize_ticket_summary(ticket),
    })


def broadcast_ticket_resolved(ticket):
    _broadcast_to_admins('ticket_resolved', {
        'ticket': serialize_ticket_summary(ticket),
    })


def _broadcast_to_admins(event_type, payload):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)('admins', {
            'type': event_type,
            **payload,
        })
    except Exception as e:
        logger.warning(f'broadcast failed ({event_type}): {e}')

def broadcast_ticket_detail_change(ticket, actor=None, step_name=''):
    """
    Push a status change to anyone viewing the ticket detail page.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    try:
        async_to_sync(channel_layer.group_send)(f'ticket_{ticket.id}', {
            'type': 'ticket_status_change',
            'ticket_id': ticket.id,
            'status': ticket.status,
            'status_display': ticket.get_status_display(),
            'ageing_color': ticket.ageing_color,
            'step_name': step_name,
            'actor_name': (actor.get_full_name() or actor.username) if actor else '',
        })
    except Exception as e:
        logger.warning(f'detail broadcast failed: {e}')


def broadcast_ticket_comment(ticket, comment):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)(f'ticket_{ticket.id}', {
            'type': 'new_comment',
            'ticket_id': ticket.id,
            'author': comment.author.get_full_name() or comment.author.username,
            'body': comment.body,
            'created_at': comment.created_at.isoformat(),
        })
    except Exception as e:
        logger.warning(f'comment broadcast failed: {e}')