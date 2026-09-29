"""
Department and system health scoring.

Composite score 0-100 combining:
  - Resolution speed (vs SLA)
  - Backlog size
  - Ageing tickets
  - Reopened rate
  - Avg resolution time

Higher score = healthier department.
"""
import logging
from datetime import timedelta

from django.utils import timezone
from django.db.models import Count, Avg, Q

from apps.tickets.models import CampusTicket
from apps.core.services import ConfigService
from apps.core.constants import (
    TICKET_STATUS_PENDING, TICKET_STATUS_IN_PROGRESS,
    TICKET_STATUS_RESOLVED, TICKET_STATUS_REOPENED,
)
from .stats_utils import clamp

logger = logging.getLogger(__name__)


def compute_department_health():
    """
    Return list of {department, display, score, breakdown, status_label}.
    """
    results = []
    for dept in ConfigService.departments(active_only=True):
        score_data = _score_department(dept.code)
        if score_data is None:
            continue
        results.append({
            'department': dept.code,
            'display': dept.name,
            'icon': dept.icon,
            **score_data,
        })

    # Sort: worst first
    results.sort(key=lambda r: r['score'])
    return results


def _score_department(dept_code):
    """Compute health score for one department."""
    tickets = CampusTicket.objects.filter(assigned_department=dept_code, is_deleted=False)
    total = tickets.count()

    if total == 0:
        return None

    now = timezone.now()

    # --- Component 1: Backlog (open / total) ---
    open_count = tickets.filter(
        status__in=[TICKET_STATUS_PENDING, TICKET_STATUS_IN_PROGRESS]
    ).count()
    backlog_ratio = open_count / total

    # --- Component 2: Ageing (proportion of open tickets that are red) ---
    open_tickets = tickets.filter(
        status__in=[TICKET_STATUS_PENDING, TICKET_STATUS_IN_PROGRESS]
    )
    red_count = sum(1 for t in open_tickets if t.ageing_color == 'red')
    red_ratio = (red_count / open_count) if open_count else 0

    # --- Component 3: Reopen rate ---
    reopened_count = tickets.filter(status=TICKET_STATUS_REOPENED).count()
    resolved_count = tickets.filter(status=TICKET_STATUS_RESOLVED).count()
    reopen_rate = reopened_count / max(1, resolved_count + reopened_count)

    # --- Component 4: Avg resolution vs SLA ---
    recent_resolved = tickets.filter(
        status=TICKET_STATUS_RESOLVED,
        resolved_at__gte=now - timedelta(days=30),
        resolved_at__isnull=False,
    )
    avg_resolution_hours = 0
    if recent_resolved.exists():
        durations = [
            (t.resolved_at - t.created_at).total_seconds() / 3600
            for t in recent_resolved
        ]
        avg_resolution_hours = sum(durations) / len(durations)

    # Target SLA for this dept
    base_sla = 48  # fallback
    # Look up config
    tts = ConfigService.ticket_types()
    if tts:
        base_sla = tts[0].sla_hours   # Use first ticket type as proxy
    sla_ratio = avg_resolution_hours / base_sla if base_sla else 1.0

    # --- Composite score (0-100) ---
    score = 100
    score -= backlog_ratio * 25         # up to -25 for full backlog
    score -= red_ratio * 30             # up to -30 if all tickets red
    score -= reopen_rate * 15           # up to -15 for full reopen
    score -= clamp(sla_ratio - 1, 0, 2) * 15   # up to -30 if 2x SLA
    score = clamp(score, 0, 100)

    # Status label
    if score >= 80:
        status = 'healthy'
    elif score >= 60:
        status = 'watch'
    elif score >= 40:
        status = 'at_risk'
    else:
        status = 'critical'

    return {
        'score': round(score, 1),
        'status': status,
        'breakdown': {
            'total': total,
            'open': open_count,
            'red_aging': red_count,
            'reopened': reopened_count,
            'avg_resolution_hours': round(avg_resolution_hours, 1),
        },
        'factors': {
            'backlog': round(backlog_ratio * 100, 1),
            'ageing': round(red_ratio * 100, 1),
            'reopen': round(reopen_rate * 100, 1),
            'sla_ratio': round(sla_ratio, 2),
        }
    }


def compute_system_health():
    """Overall system health — average of departments weighted by volume."""
    depts = compute_department_health()
    if not depts:
        return {'score': 100, 'status': 'healthy', 'departments': []}

    total_tickets = sum(d['breakdown']['total'] for d in depts) or 1
    weighted_score = sum(
        d['score'] * d['breakdown']['total'] for d in depts
    ) / total_tickets

    if weighted_score >= 80:
        status = 'healthy'
    elif weighted_score >= 60:
        status = 'watch'
    elif weighted_score >= 40:
        status = 'at_risk'
    else:
        status = 'critical'

    return {
        'score': round(weighted_score, 1),
        'status': status,
        'departments': depts,
    }