"""
NotificationService — the central API for creating and delivering notifications.

Usage:
    from apps.notifications.services import NotificationService

    NotificationService.notify(
        recipient=user,
        event_code='ticket.resolved',
        context={'ticket': ticket, ...},
    )

    # Or specialized:
    NotificationService.notify_ticket_event(ticket, 'ticket.resolved', extra={...})
"""
import logging
from typing import Optional, Dict, Any, List

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.services import ConfigService
from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:

    # =================================================================
    # Core API
    # =================================================================
    @classmethod
    def notify(
        cls,
        recipient,
        event_code: str,
        context: Dict[str, Any],
        link_url: str = '',
        target=None,
        priority: str = 'normal',
        force_channels: Optional[List[str]] = None,
    ) -> Optional[Notification]:
        """
        Create a notification and dispatch to configured channels.

        Returns the created Notification, or None on failure.
        Never raises.
        """
        try:
            prefs = NotificationPreference.for_user(recipient)

            # Check user wants this event
            if not prefs.wants_event(event_code):
                logger.debug(f"User {recipient.username} opted out of {event_code}")
                return None

            # Render templates
            in_app_tpl = ConfigService.get_notification_template(
                event_code, 'in_app', recipient.language_pref or 'en'
            )
            email_tpl = ConfigService.get_notification_template(
                event_code, 'email', recipient.language_pref or 'en'
            )
            sms_tpl = ConfigService.get_notification_template(
                event_code, 'sms', recipient.language_pref or 'en'
            )

            # Render in-app (always — it's the record of truth)
            title, body = cls._render(in_app_tpl, context)

            if not title:
                title = cls._default_title(event_code, context)

            if not body:
                body = cls._default_body(event_code, context)

            notification = Notification.objects.create(
                recipient=recipient,
                event_code=event_code,
                title=title,
                body=body,
                link_url=link_url,
                priority=priority,
                icon=cls._icon_for(event_code),
                target_model=target._meta.label if target else '',
                target_id=str(target.pk) if target else '',
            )

            # Determine which channels to dispatch
            channels = force_channels or []

            if not force_channels:
                if prefs.email_enabled:
                    channels.append('email')

                if prefs.sms_enabled:
                    channels.append('sms')

                # in_app is always considered delivered by creating the row

            # Dispatch to non-in-app channels
            logs = {
                'in_app': {
                    'sent': True,
                    'at': timezone.now().isoformat()
                }
            }

            for channel in channels:
                result = cls._dispatch(
                    channel,
                    recipient,
                    email_tpl,
                    sms_tpl,
                    title,
                    body,
                    context
                )
                logs[channel] = result

            notification.delivery_logs = logs

            notification.save(
                update_fields=['delivery_logs', 'updated_at']
            )

            # Push to WebSocket if user is connected
            try:
                from .pusher import push_notification
                push_notification(notification)
            except Exception as e:
                logger.warning(f'WS push failed: {e}')

            logger.info(
                f"Notification created: {event_code} -> {recipient.username} "
                f"(channels: {channels})"
            )

            return notification

        except Exception as e:
            logger.exception(
                f"Notification failed for {event_code}: {e}"
            )
            return None

    # =================================================================
    # Specialized helpers
    # =================================================================
    @classmethod
    def notify_ticket_event(
        cls,
        ticket,
        event_code: str,
        extra: Optional[Dict] = None,
        recipients: Optional[List] = None,
    ):
        """
        Notify about a ticket event.
        Default recipients: the student who filed it.
        """
        context = cls._ticket_context(ticket)

        if extra:
            context.update(extra)

        if recipients is None:
            recipients = [ticket.student]

        results = []

        for r in recipients:
            n = cls.notify(
                recipient=r,
                event_code=event_code,
                context=context,
                link_url=f"/tickets/{ticket.id}/",
                target=ticket,
                priority=cls._priority_for_ticket(ticket),
            )

            if n:
                results.append(n)

        return results

    @classmethod
    def notify_step_action(
        cls,
        ticket,
        step_execution,
        actor,
        action
    ):
        """Notify relevant people about a workflow step action."""

        # 1. Notify the student (submitter)
        cls.notify_ticket_event(
            ticket,
            event_code='ticket.step_action',
            extra={
                'step_name': step_execution.workflow_step.name,
                'action': action,
                'actor_name': actor.get_full_name() or actor.username,
                'comment': step_execution.comment or '',
            },
        )

        # 2. Notify the next approver (if any)
        from apps.workflows.engine import WorkflowEngine

        next_step = WorkflowEngine.current_step(ticket)

        if next_step:
            for approver in cls._approvers_for_step(next_step):
                cls.notify(
                    recipient=approver,
                    event_code='step.pending',
                    context={
                        **cls._ticket_context(ticket),
                        'step_name': next_step.workflow_step.name,
                        'instructions': next_step.workflow_step.instructions,
                        'actor_name': actor.get_full_name() or actor.username,
                    },
                    link_url=f"/tickets/{ticket.id}/resolve/",
                    target=ticket,
                    priority='high',
                )

    @classmethod
    def notify_notice_published(cls, notice, students):
        """Notify all targeted students about a new notice."""

        context = {
            'notice_title': notice.title,
            'notice_summary': notice.ai_summary or notice.content[:120],
            'priority': notice.ai_priority,
            'posted_by': (
                notice.posted_by.get_full_name()
                or notice.posted_by.username
            ),
        }

        for s in students:
            cls.notify(
                recipient=s,
                event_code='notice.published',
                context=context,
                link_url=f"/notices/{notice.id}/",
                target=notice,
                priority=(
                    'high'
                    if notice.ai_priority == 'high'
                    else 'normal'
                ),
            )

    # =================================================================
    # Internal helpers
    # =================================================================
    @classmethod
    def _render(cls, template, context):
        """Render a template safely."""

        if not template:
            return '', ''

        try:
            subject, body = template.render(context)
            return subject, body

        except Exception as e:
            logger.warning(
                f"Template render failed: {e}"
            )
            return '', ''

    @classmethod
    def _dispatch(
        cls,
        channel,
        recipient,
        email_tpl,
        sms_tpl,
        title,
        body,
        context
    ):
        """Dispatch to one channel. Returns a delivery log dict."""

        result = {
            'sent': False,
            'at': timezone.now().isoformat(),
            'error': None
        }

        try:
            if channel == 'email':

                if not recipient.email:
                    result['error'] = 'no email address'
                    return result

                subject, email_body = cls._render(
                    email_tpl,
                    context
                )

                subject = subject or title
                email_body = email_body or body

                cls._send_email(
                    recipient.email,
                    subject,
                    email_body
                )

                result['sent'] = True

            elif channel == 'sms':

                phone = getattr(
                    recipient,
                    'phone',
                    ''
                )

                if not phone:
                    result['error'] = 'no phone number'
                    return result

                _, sms_body = cls._render(
                    sms_tpl,
                    context
                )

                sms_body = sms_body or body[:160]

                cls._send_sms(
                    phone,
                    sms_body
                )

                result['sent'] = True

        except Exception as e:
            logger.exception(
                f"Dispatch failed on {channel}: {e}"
            )
            result['error'] = str(e)

        return result

    @classmethod
    def _send_email(cls, to_address, subject, body):
        """Send email via configured backend."""

        from django.core.mail import send_mail
        from django.conf import settings

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_address],
            fail_silently=False,
        )

        logger.info(
            f"[EMAIL] → {to_address}: {subject}"
        )

    @classmethod
    def _send_sms(cls, phone, body):
        """Send SMS via pluggable provider."""

        from apps.notifications.sms_providers import get_sms_provider

        provider = get_sms_provider()

        result = provider.send(
            phone,
            body
        )

        logger.info(
            f"[SMS/{provider.name}] → {phone}: "
            f"{body[:50]}… (ok={result.get('ok')})"
        )

    @classmethod
    def _ticket_context(cls, ticket):
        """Build the context dict for ticket-related notifications."""

        ticket_type = getattr(
            ticket,
            'ticket_type',
            ''
        ) or ''

        if hasattr(ticket, 'get_ticket_type_display'):
            try:
                ticket_type = ticket.get_ticket_type_display()
            except Exception:
                pass

        ticket_status = getattr(
            ticket,
            'status',
            ''
        ) or ''

        if hasattr(ticket, 'get_status_display'):
            try:
                ticket_status = ticket.get_status_display()
            except Exception:
                pass

        priority = getattr(
            ticket,
            'priority',
            ''
        ) or ''

        if hasattr(ticket, 'get_priority_display'):
            try:
                priority = ticket.get_priority_display()
            except Exception:
                pass

        assigned_department = getattr(
            ticket,
            'assigned_department',
            ''
        ) or ''

        student = getattr(
            ticket,
            'student',
            None
        )

        if student:
            student_name = (
                student.get_full_name()
                or student.username
            )
            student_username = student.username
        else:
            student_name = ''
            student_username = ''

        return {
            'ticket_id': ticket.id,
            'ticket_subject': getattr(
                ticket,
                'subject',
                ''
            ) or '',
            'ticket_type': ticket_type,
            'ticket_status': ticket_status,
            'assigned_department': assigned_department,
            'priority': priority,
            'student_name': student_name,
            'student_username': student_username,
            'resolution_note': getattr(
                ticket,
                'resolution_note',
                ''
            ) or '',
            'age_hours': getattr(
                ticket,
                'age_hours',
                0
            ),
        }

    @classmethod
    def _approvers_for_step(cls, step_execution):
        """Return list of users who can act on this step."""

        step = step_execution.workflow_step

        if step.specific_user_id:
            return [step.specific_user]

        if step.role_required:
            return list(
                User.objects.filter(
                    role=step.role_required,
                    is_active=True
                )
            )

        return list(
            User.objects.filter(
                role__in=[
                    'warden',
                    'hod',
                    'dean',
                    'principal'
                ],
                is_active=True
            )
        )

    @classmethod
    def _priority_for_ticket(cls, ticket):

        if ticket.priority == 'urgent':
            return 'urgent'

        if ticket.priority == 'high':
            return 'high'

        return 'normal'

    @classmethod
    def _icon_for(cls, event_code):

        mapping = {
            'ticket.created': '📩',
            'ticket.assigned': '👤',
            'ticket.resolved': '✅',
            'ticket.escalated': '🚨',
            'ticket.step_action': '🔄',
            'step.pending': '⏳',
            'notice.published': '📢',
            'feedback.acknowledged': '💬',
            'document.issued': '📄',
        }

        return mapping.get(
            event_code,
            '🔔'
        )

    @classmethod
    def _default_title(cls, event_code, context):

        titles = {
            'ticket.created':
                f"Ticket #{context.get('ticket_id')} received",

            'ticket.assigned':
                f"Ticket #{context.get('ticket_id')} assigned",

            'ticket.resolved':
                f"Ticket #{context.get('ticket_id')} resolved",

            'ticket.escalated':
                f"Ticket #{context.get('ticket_id')} escalated",

            'step.pending':
                f"Action needed: "
                f"{context.get('step_name', 'workflow step')}",

            'notice.published':
                context.get(
                    'notice_title',
                    'New notice'
                ),
        }

        return titles.get(
            event_code,
            'Notification'
        )

    @classmethod
    def _default_body(cls, event_code, context):

        bodies = {
            'ticket.created': (
                f"Your ticket #{context.get('ticket_id')} "
                f"has been received. "
                f"Current status: "
                f"{context.get('ticket_status')}."
            ),

            'ticket.resolved': (
                f"Ticket #{context.get('ticket_id')} resolved: "
                f"{context.get('resolution_note', '')}"
            ),

            'step.pending': (
                f"Ticket #{context.get('ticket_id')} "
                f"requires your action on step: "
                f"{context.get('step_name')}."
            ),
        }

        return bodies.get(
            event_code,
            ''
        )