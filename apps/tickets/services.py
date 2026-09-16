"""
Ticket lifecycle services.
AI pipeline calls will be wired here in Step 5.
"""
# from django.utils import timezone
# from .models import CampusTicket


# def create_ticket(student, ticket_type, raw_input, subject=None, attachment=None):
#     """
#     Create a ticket with pending status.
#     AI formatting/routing happens later — this keeps it synchronous & testable.
#     """
#     ticket = CampusTicket.objects.create(
#         student=student,
#         ticket_type=ticket_type,
#         subject=subject or raw_input[:200],
#         raw_input=raw_input,
#         attachment=attachment,
#     )
#     return ticket


# def assign_ticket(ticket, department=None, admin_user=None, priority=None):
#     """Assign routing fields."""
#     if department:
#         ticket.assigned_department = department
#     if admin_user:
#         ticket.assigned_to = admin_user
#     if priority:
#         ticket.priority = priority
#     if ticket.status == 'pending':
#         ticket.status = 'in_progress'
#     ticket.save()
#     return ticket


# def resolve_ticket(ticket, admin_user, resolution_note):
#     ticket.status = 'resolved'
#     ticket.resolution_note = resolution_note
#     ticket.resolved_by = admin_user
#     ticket.resolved_at = timezone.now()
#     ticket.save()
#     return ticket


# def confirm_resolution(ticket, fixed):
#     """Student confirms (True) or reopens (False)."""
#     ticket.student_confirmed = fixed
#     if not fixed:
#         ticket.status = 'reopened'
#         ticket.priority = 'high'
#     ticket.save()
#     return ticket

"""
Ticket lifecycle services.
AI enrichment happens here via ai_engine.pipelines.
"""
from django.utils import timezone
from .models import CampusTicket


def create_ticket(student, ticket_type, raw_input, subject=None, attachment=None,
                  enrich=True):
    """
    Create a ticket with pending status.
    If enrich=True, calls AI pipeline to:
      - assign department
      - classify priority
      - generate formal body
    """
    ticket = CampusTicket.objects.create(
        student=student,
        ticket_type=ticket_type,
        subject=subject or raw_input[:200],
        raw_input=raw_input,
        attachment=attachment,
    )

    if enrich:
        from ai_engine.pipelines import process_new_ticket
        process_new_ticket(ticket, save=True)

    return ticket


def assign_ticket(ticket, department=None, admin_user=None, priority=None):
    if department:
        ticket.assigned_department = department
    if admin_user:
        ticket.assigned_to = admin_user
    if priority:
        ticket.priority = priority
    if ticket.status == 'pending':
        ticket.status = 'in_progress'
    ticket.save()
    return ticket


def resolve_ticket(ticket, admin_user, resolution_note):
    ticket.status = 'resolved'
    ticket.resolution_note = resolution_note
    ticket.resolved_by = admin_user
    ticket.resolved_at = timezone.now()
    ticket.save()
    return ticket


def confirm_resolution(ticket, fixed):
    ticket.student_confirmed = fixed
    if not fixed:
        ticket.status = 'reopened'
        ticket.priority = 'high'
    ticket.save()
    return ticket