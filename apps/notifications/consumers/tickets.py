"""
Ticket-related WebSocket consumers.

- AdminTicketConsumer: streams new/updated tickets to all admins
- TicketDetailConsumer: streams updates for one specific ticket
"""

import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .base import BaseUserConsumer


logger = logging.getLogger(__name__)


class AdminTicketConsumer(BaseUserConsumer):
    """
    Group: `admins` — receives broadcasts about tickets.
    Only admin roles can connect.
    """

    async def connect(self):
        user = self.scope.get('user')

        if not user or not user.is_authenticated or not user.is_admin_role():
            await self.close(code=4003)
            return

        await super().connect()

        await self.channel_layer.group_add(
            'admins',
            self.channel_name,
        )

        await self.send_json({
            'type': 'admin_connected',
        })

    async def disconnect(self, code):
        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.channel_layer.group_discard(
                'admins',
                self.channel_name,
            )

        await super().disconnect(code)

    # -------- Group event handlers --------

    async def ticket_created(self, event):
        await self.send_json({
            'type': 'ticket_created',
            'ticket': event.get('ticket', {}),
        })

    async def ticket_updated(self, event):
        await self.send_json({
            'type': 'ticket_updated',
            'ticket': event.get('ticket', {}),
        })

    async def ticket_resolved(self, event):
        await self.send_json({
            'type': 'ticket_resolved',
            'ticket': event.get('ticket', {}),
        })


class TicketDetailConsumer(BaseUserConsumer):
    """
    Group: `ticket_<id>` — receives updates for one specific ticket.
    Both the student who owns it and any admin can connect.
    """

    async def connect(self):
        user = self.scope.get('user')

        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']

        # Verify access
        can_access = await self.check_access(
            user,
            self.ticket_id,
        )

        if not can_access:
            await self.close(code=4003)
            return

        await super().connect()

        self.ticket_group = f'ticket_{self.ticket_id}'

        await self.channel_layer.group_add(
            self.ticket_group,
            self.channel_name,
        )

        await self.send_json({
            'type': 'ticket_detail_connected',
            'ticket_id': self.ticket_id,
        })

    async def disconnect(self, code):
        if hasattr(self, 'ticket_group'):
            await self.channel_layer.group_discard(
                self.ticket_group,
                self.channel_name,
            )

        await super().disconnect(code)

    @database_sync_to_async
    def check_access(self, user, ticket_id):
        from apps.tickets.models import CampusTicket

        try:
            ticket = CampusTicket.objects.get(pk=ticket_id)
        except CampusTicket.DoesNotExist:
            return False

        if user.is_admin_role():
            return True

        return ticket.student_id == user.id

    async def ticket_status_change(self, event):
        await self.send_json({
            'type': 'ticket_status_change',
            'ticket_id': event.get('ticket_id'),
            'status': event.get('status'),
            'status_display': event.get('status_display'),
            'ageing_color': event.get('ageing_color'),
            'step_name': event.get('step_name', ''),
            'actor_name': event.get('actor_name', ''),
        })

    async def new_comment(self, event):
        await self.send_json({
            'type': 'new_comment',
            'ticket_id': event.get('ticket_id'),
            'author': event.get('author'),
            'body': event.get('body'),
            'created_at': event.get('created_at'),
        })