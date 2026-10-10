"""
Ticket lifecycle services with audit logging.
"""
from django.utils import timezone

from apps.core.audit import AuditService
from .models import CampusTicket


def create_ticket(student, ticket_type, raw_input, subject=None, attachment=None,
                  enrich=True):
    """
    Create ticket with config-driven defaults.
    Priority defaults to the 'medium' level from PriorityLevel config.
    """
    from apps.core.services import ConfigService

    default_priority = 'medium'
    medium = ConfigService.priority_by_code('medium')
    if medium:
        default_priority = medium.code
    else:
        # Fallback: pick the middle-weight priority
        priorities = ConfigService.priority_levels()
        if priorities:
            default_priority = priorities[len(priorities) // 2].code

    ticket = CampusTicket.objects.create(
        student=student,
        ticket_type=ticket_type,
        subject=subject or raw_input[:200],
        raw_input=raw_input,
        attachment=attachment,
        priority=default_priority,
    )

    if enrich:
        from ai_engine.pipelines import process_new_ticket
        process_new_ticket(ticket, save=True)

    # Attach workflow
    try:
        from apps.workflows.engine import WorkflowEngine
        workflow = WorkflowEngine.attach_workflow(ticket)
        if workflow:
            ticket.ai_metadata = {
                **(ticket.ai_metadata or {}),
                'workflow': workflow.code,
            }
            ticket.save(update_fields=['ai_metadata'])
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(
            f"Failed to attach workflow to ticket #{ticket.id}: {e}"
        )

    AuditService.log_action(
        action='create',
        target=ticket,
        metadata={
            'ticket_type': ticket_type,
            'assigned_department': ticket.assigned_department,
            'priority': ticket.priority,
            'via': 'student_portal',
        },
        user=student,
    )

    # Notify the student (always)
    try:
        from apps.notifications.services import NotificationService

        NotificationService.notify_ticket_event(
            ticket,
            'ticket.created',
            recipients=[student],
        )

        # The workflow engine automatically notifies the first approver

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(
            f"ticket.created notify failed: {e}"
        )

    # Broadcast to admins
    try:
        from apps.notifications.broadcasters import broadcast_ticket_created
        broadcast_ticket_created(ticket)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(
            f"ticket broadcast failed: {e}"
        )

    return ticket


def assign_ticket(ticket, department=None, admin_user=None, priority=None):
    old = {
        'assigned_department': ticket.assigned_department,
        'assigned_to_id': ticket.assigned_to_id,
        'priority': ticket.priority,
        'status': ticket.status,
    }

    if department:
        ticket.assigned_department = department

    if admin_user:
        ticket.assigned_to = admin_user

    if priority:
        ticket.priority = priority

    if ticket.status == 'pending':
        ticket.status = 'in_progress'

    ticket.save()

    new = {
        'assigned_department': ticket.assigned_department,
        'assigned_to_id': ticket.assigned_to_id,
        'priority': ticket.priority,
        'status': ticket.status,
    }

    AuditService.log_config_change(
        instance=ticket,
        old_values=old,
        new_values=new,
        user=admin_user,
    )

    return ticket


def resolve_ticket(ticket, admin_user, resolution_note):
    ticket.status = 'resolved'
    ticket.resolution_note = resolution_note
    ticket.resolved_by = admin_user
    ticket.resolved_at = timezone.now()
    ticket.save()

    try:
        from apps.notifications.broadcasters import broadcast_ticket_resolved
        broadcast_ticket_resolved(ticket)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(
            f"resolve broadcast failed: {e}"
        )

    AuditService.log_action(
        action='resolve',
        target=ticket,
        metadata={
            'resolution_note': resolution_note[:200],
        },
        user=admin_user,
    )

    # Notify student that the ticket was resolved
    try:
        from apps.notifications.services import NotificationService

        NotificationService.notify_ticket_event(
            ticket,
            'ticket.resolved',
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(
            f"ticket.resolved notify failed: {e}"
        )

    return ticket


def confirm_resolution(ticket, fixed):
    ticket.student_confirmed = fixed

    if not fixed:
        ticket.status = 'reopened'
        ticket.priority = 'high'

    ticket.save()

    AuditService.log_action(
        action='approve' if fixed else 'reject',
        target=ticket,
        metadata={
            'student_confirmed': fixed,
            'reopened': not fixed,
        },
        user=ticket.student,
    )

    return ticket