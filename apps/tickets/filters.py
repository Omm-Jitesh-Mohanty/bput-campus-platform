"""
Filter logic for the admin ticket queue.
Returns a queryset given request.GET parameters.
"""
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import CampusTicket
from apps.core.constants import (
    TICKET_STATUS_PENDING, TICKET_STATUS_IN_PROGRESS,
    TICKET_STATUS_RESOLVED, TICKET_STATUS_REOPENED,
)


def apply_filters(request, qs):
    """Apply URL query filters to the ticket queryset."""
    # Status filter
    status = request.GET.get('status', '').strip()
    if status in [TICKET_STATUS_PENDING, TICKET_STATUS_IN_PROGRESS,
                  TICKET_STATUS_RESOLVED, TICKET_STATUS_REOPENED]:
        qs = qs.filter(status=status)

    # Department filter
    department = request.GET.get('department', '').strip()
    if department:
        qs = qs.filter(assigned_department=department)

    # Priority filter
    priority = request.GET.get('priority', '').strip()
    if priority:
        qs = qs.filter(priority=priority)

    # Type filter
    ticket_type = request.GET.get('type', '').strip()
    if ticket_type:
        qs = qs.filter(ticket_type=ticket_type)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(subject__icontains=q)
            | Q(raw_input__icontains=q)
            | Q(student__username__icontains=q)
            | Q(student__first_name__icontains=q)
            | Q(student__last_name__icontains=q)
        )

    # Ageing filter (special)
    ageing = request.GET.get('ageing', '').strip()
    if ageing:
        now = timezone.now()
        open_qs = qs.exclude(status=TICKET_STATUS_RESOLVED)
        if ageing == 'fresh':
            cutoff = now - timedelta(hours=24)
            qs = open_qs.filter(created_at__gte=cutoff)
        elif ageing == 'warning':
            start = now - timedelta(hours=48)
            end = now - timedelta(hours=24)
            qs = open_qs.filter(created_at__lt=end, created_at__gte=start)
        elif ageing == 'critical':
            start = now - timedelta(hours=72)
            end = now - timedelta(hours=48)
            qs = open_qs.filter(created_at__lt=end, created_at__gte=start)
        elif ageing == 'overdue':
            cutoff = now - timedelta(hours=72)
            qs = open_qs.filter(created_at__lt=cutoff)

    return qs


def active_filters(request):
    """Return dict of active filters for template rendering."""
    keys = ['status', 'department', 'priority', 'type', 'q', 'ageing']
    return {k: request.GET.get(k, '') for k in keys if request.GET.get(k)}