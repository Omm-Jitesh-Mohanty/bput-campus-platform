"""
Predict which open tickets will breach their SLA in the next N hours.

Method: for each open ticket, compute hours_remaining until red threshold.
If remaining <= 0 → already breached.
If 0 < remaining <= window → will breach within window.
"""
import logging
from django.utils import timezone

from apps.tickets.models import CampusTicket
from apps.core.services import ConfigService
from apps.core.constants import TICKET_STATUS_PENDING, TICKET_STATUS_IN_PROGRESS

logger = logging.getLogger(__name__)


def predict_sla_breaches(hours_ahead=24):
    """
    Return dict with:
      - count: total tickets that will breach
      - breached: already breached
      - at_risk: list of {ticket_id, subject, hours_remaining, priority, department}
      - by_department: {dept_code: count}
    """
    now = timezone.now()
    window_end = now + timezone.timedelta(hours=hours_ahead)

    open_tickets = CampusTicket.objects.filter(
        status__in=[TICKET_STATUS_PENDING, TICKET_STATUS_IN_PROGRESS],
        is_deleted=False,
    ).select_related('student')

    breached = []
    at_risk = []
    by_dept = {}

    for t in open_tickets:
        sla = ConfigService.sla_hours_for(t.ticket_type, t.priority)
        red_hours = sla.get('red', 72)
        threshold_time = t.created_at + timezone.timedelta(hours=red_hours)

        if threshold_time <= now:
            breached.append(t)
        elif threshold_time <= window_end:
            hours_remaining = (threshold_time - now).total_seconds() / 3600
            at_risk.append({
                'ticket_id': t.id,
                'subject': t.subject[:80],
                'priority': t.priority,
                'department': t.assigned_department,
                'hours_remaining': round(hours_remaining, 1),
                'age_hours': t.age_hours,
                'red_threshold_hours': red_hours,
            })
            by_dept[t.assigned_department] = by_dept.get(t.assigned_department, 0) + 1

    # Sort at-risk by urgency
    at_risk.sort(key=lambda x: x['hours_remaining'])

    return {
        'count': len(breached) + len(at_risk),
        'breached_count': len(breached),
        'at_risk_count': len(at_risk),
        'at_risk': at_risk[:20],       # cap for display
        'breached': [
            {
                'ticket_id': t.id,
                'subject': t.subject[:80],
                'age_hours': t.age_hours,
                'department': t.assigned_department,
            }
            for t in breached[:20]
        ],
        'by_department': by_dept,
        'window_hours': hours_ahead,
    }