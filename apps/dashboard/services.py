"""
Admin dashboard aggregation services.
All heavy queries live here — views just call these and pass to templates.
"""

from datetime import timedelta

from django.utils import timezone
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField

from apps.tickets.models import CampusTicket
from apps.notices.models import Notice, NoticeReadStatus
from apps.feedback.models import Feedback
from apps.accounts.models import User

from apps.core.constants import (
    TICKET_STATUS_PENDING,
    TICKET_STATUS_IN_PROGRESS,
    TICKET_STATUS_RESOLVED,
    TICKET_STATUS_REOPENED,
)


def _avg_resolution_hours(qs, since):
    resolved = qs.filter(
        status='resolved',
        resolved_at__gte=since,
        resolved_at__isnull=False,
    )

    if not resolved.exists():
        return 0.0

    durations = [
        (t.resolved_at - t.created_at).total_seconds() / 3600
        for t in resolved
    ]

    return round(sum(durations) / len(durations), 1)


# =====================================================================
# 1. KPI TILES (top of dashboard)
# =====================================================================
def get_ticket_kpis():
    """Return dict of headline numbers for the KPI cards."""
    now = timezone.now()
    qs = CampusTicket.objects.filter(is_deleted=False)

    pending = qs.filter(status=TICKET_STATUS_PENDING).count()
    in_progress = qs.filter(status=TICKET_STATUS_IN_PROGRESS).count()
    resolved = qs.filter(status=TICKET_STATUS_RESOLVED).count()
    reopened = qs.filter(status=TICKET_STATUS_REOPENED).count()

    # Average age of open tickets (pending + in-progress)
    open_tickets = qs.filter(
        status__in=[
            TICKET_STATUS_PENDING,
            TICKET_STATUS_IN_PROGRESS,
        ]
    )

    avg_age = 0.0

    if open_tickets.exists():
        total_age = sum(t.age_hours for t in open_tickets)
        avg_age = round(
            total_age / open_tickets.count(),
            1,
        )

    # Average resolution time (last 30 days, resolved tickets)
    thirty_days_ago = now - timedelta(days=30)

    recent_resolved = qs.filter(
        status=TICKET_STATUS_RESOLVED,
        resolved_at__gte=thirty_days_ago,
    )

    avg_resolution_hours = 0.0

    if recent_resolved.exists():
        durations = [
            (t.resolved_at - t.created_at).total_seconds() / 3600
            for t in recent_resolved
        ]

        avg_resolution_hours = round(
            sum(durations) / len(durations),
            1,
        )

    # Overdue (red-ageing) open tickets
    overdue = sum(
        1
        for t in open_tickets
        if t.ageing_color == 'red'
    )

    return {
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved,
        'reopened': reopened,
        'total_open': pending + in_progress,
        'avg_age_hours': avg_age,
        'avg_resolution_hours': avg_resolution_hours,
        'overdue': overdue,
    }


# =====================================================================
# 2. DEPARTMENT-WISE BREAKDOWN
# =====================================================================
def get_department_breakdown():
    """
    Return list of {department, code, total, pending, overdue, avg_age_hours}.
    Used for bar chart + department cards.
    """
    qs = (
        CampusTicket.objects
        .filter(is_deleted=False)
        .exclude(assigned_department='')
    )

    # Aggregate counts
    dept_counts = (
        qs.values('assigned_department')
        .annotate(
            total=Count('id'),
            pending=Count(
                'id',
                filter=Q(status=TICKET_STATUS_PENDING),
            ),
            in_progress=Count(
                'id',
                filter=Q(status=TICKET_STATUS_IN_PROGRESS),
            ),
            resolved=Count(
                'id',
                filter=Q(status=TICKET_STATUS_RESOLVED),
            ),
        )
        .order_by('-total')
    )

    results = []

    for row in dept_counts:
        dept = row['assigned_department']

        tickets = qs.filter(
            assigned_department=dept
        )

        open_tickets = tickets.filter(
            status__in=[
                TICKET_STATUS_PENDING,
                TICKET_STATUS_IN_PROGRESS,
            ]
        )

        overdue = sum(
            1
            for t in open_tickets
            if t.ageing_color == 'red'
        )

        avg_age = 0.0

        if open_tickets.exists():
            avg_age = round(
                sum(t.age_hours for t in open_tickets)
                / open_tickets.count(),
                1,
            )

        results.append({
            'department': dept,
            'display': dept.replace('_', ' ').title(),
            'total': row['total'],
            'pending': row['pending'],
            'in_progress': row['in_progress'],
            'resolved': row['resolved'],
            'overdue': overdue,
            'avg_age_hours': avg_age,
        })

    return results


# =====================================================================
# 3. TICKET TYPE BREAKDOWN (complaint / leave / document / gatepass)
# =====================================================================
def get_type_breakdown():
    qs = CampusTicket.objects.filter(is_deleted=False)

    return list(
        qs.values('ticket_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )


# =====================================================================
# 4. AGEING BUCKETS (for heatmap)
# =====================================================================
def get_ageing_buckets():
    """
    Return counts by age bucket for OPEN tickets.
    Buckets are determined per-ticket via SLAPolicy, then aggregated.
    """
    open_qs = CampusTicket.objects.filter(
        is_deleted=False,
        status__in=[
            TICKET_STATUS_PENDING,
            TICKET_STATUS_IN_PROGRESS,
        ],
    )

    buckets = {
        'fresh': {
            'label': 'Fresh',
            'count': 0,
            'color': 'green',
            'tickets': [],
        },
        'warning': {
            'label': 'Watch',
            'count': 0,
            'color': 'yellow',
            'tickets': [],
        },
        'critical': {
            'label': 'Critical',
            'count': 0,
            'color': 'orange',
            'tickets': [],
        },
        'overdue': {
            'label': 'Overdue',
            'count': 0,
            'color': 'red',
            'tickets': [],
        },
    }

    for t in open_qs:
        color = t.ageing_color

        key = {
            'green': 'fresh',
            'yellow': 'warning',
            'orange': 'critical',
            'red': 'overdue',
        }.get(color, 'fresh')

        buckets[key]['count'] += 1
        buckets[key]['tickets'].append(t)

    return buckets


# =====================================================================
# 5. RESOLUTION TIME TREND (last 14 days)
# =====================================================================
def get_resolution_trend(days=14):
    """
    Return list of {date, count, avg_hours} for tickets resolved in the last N days.
    Feeds a line chart.
    """
    now = timezone.now()
    trend = []

    for i in range(days - 1, -1, -1):
        day_start = (
            now - timedelta(days=i)
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        day_end = day_start + timedelta(days=1)

        resolved_today = CampusTicket.objects.filter(
            status=TICKET_STATUS_RESOLVED,
            resolved_at__gte=day_start,
            resolved_at__lt=day_end,
        )

        count = resolved_today.count()
        avg_hours = 0.0

        if count > 0:
            durations = [
                (
                    t.resolved_at - t.created_at
                ).total_seconds() / 3600
                for t in resolved_today
            ]

            avg_hours = round(
                sum(durations) / len(durations),
                1,
            )

        trend.append({
            'date': day_start.strftime('%d %b'),
            'count': count,
            'avg_hours': avg_hours,
        })

    return trend


# =====================================================================
# 6. RECURRING ISSUES (same subject pattern repeated)
# =====================================================================
def get_recurring_issues(threshold=2):
    """
    Find departments with >= threshold complaints in the last 30 days.
    Feeds 'repeat issue' detection.
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)

    qs = (
        CampusTicket.objects.filter(
            is_deleted=False,
            ticket_type='complaint',
            created_at__gte=thirty_days_ago,
        )
        .values('assigned_department')
        .annotate(count=Count('id'))
        .filter(count__gte=threshold)
        .order_by('-count')
    )

    return [
        {
            'department': r['assigned_department'] or 'unassigned',
            'display': (
                r['assigned_department'] or 'unassigned'
            ).replace('_', ' ').title(),
            'count': r['count'],
        }
        for r in qs
    ]


# =====================================================================
# 7. NOTICE REACH
# =====================================================================
def get_notice_reach(limit=8):
    """Latest notices with read %."""
    notices = (
        Notice.objects
        .filter(is_published=True)
        .order_by('-created_at')[:limit]
    )

    rows = []

    for n in notices:
        total = n.total_targeted()
        read = n.read_count()
        pct = round(
            (read / total) * 100,
            1,
        ) if total > 0 else 0.0

        rows.append({
            'id': n.id,
            'title': n.title,
            'priority': n.ai_priority,
            'total': total,
            'read': read,
            'pct': pct,
        })

    return rows


# =====================================================================
# 8. FEEDBACK SUMMARY (quantitative — no AI)
# =====================================================================
def get_feedback_summary():
    qs = Feedback.objects.all()
    total = qs.count()

    if total == 0:
        return {
            'total': 0,
            'avg_rating': 0.0,
            'by_category': [],
            'rating_distribution': {
                i: 0 for i in range(1, 6)
            },
        }

    avg = qs.aggregate(
        avg=Avg('rating')
    )['avg'] or 0.0

    by_cat = list(
        qs.values('category')
        .annotate(
            count=Count('id'),
            avg_rating=Avg('rating'),
        )
        .order_by('-count')
    )

    rating_dist = {
        i: 0 for i in range(1, 6)
    }

    for row in qs.values('rating').annotate(
        c=Count('id')
    ):
        rating_dist[row['rating']] = row['c']

    return {
        'total': total,
        'avg_rating': round(avg, 2),
        'by_category': by_cat,
        'rating_distribution': rating_dist,
    }


# =====================================================================
# 9. WORKLOAD DISTRIBUTION (per admin)
# =====================================================================
def get_workload_distribution():
    """Return list of {admin, open_count, resolved_count}."""
    admins = User.objects.filter(
        role__in=[
            'teacher',
            'warden',
            'hod',
            'dean',
            'principal',
        ]
    )

    rows = []

    for a in admins:
        open_count = CampusTicket.objects.filter(
            assigned_to=a,
            status__in=[
                TICKET_STATUS_PENDING,
                TICKET_STATUS_IN_PROGRESS,
            ],
        ).count()

        resolved_count = CampusTicket.objects.filter(
            resolved_by=a,
            status=TICKET_STATUS_RESOLVED,
        ).count()

        if open_count + resolved_count > 0:
            rows.append({
                'admin': a.get_full_name() or a.username,
                'role': a.get_role_display(),
                'open': open_count,
                'resolved': resolved_count,
            })

    rows.sort(
        key=lambda r: r['open'],
        reverse=True,
    )

    return rows


# =====================================================================
# 10. RECENT AUDIT ACTIVITY
# =====================================================================
def get_recent_audit_activity(limit=10):
    """Return the last N audit events for the dashboard widget."""
    from apps.core.models import AuditLog

    return (
        AuditLog.objects
        .select_related('user')
        .order_by('-timestamp')[:limit]
    )