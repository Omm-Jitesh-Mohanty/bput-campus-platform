"""
Dashboard analytics v2 — all metrics the executive dashboard needs.
"""
import logging
from datetime import timedelta
from collections import Counter, defaultdict

from django.db.models import Count, Avg, Q
from django.utils import timezone

from apps.tickets.models import CampusTicket
from apps.accounts.models import User
from apps.attendance.models import AttendanceRecord
from apps.notices.models import Notice, NoticeReadStatus
from apps.feedback.models import Feedback
from apps.core.services import ConfigService
from apps.workflows.models import TicketStepExecution

logger = logging.getLogger(__name__)


# =====================================================================
# Filters
# =====================================================================
def apply_dashboard_filters(qs, filters):
    """Apply user-selected filters to the ticket queryset."""
    days = int(filters.get('days') or 30)
    since = timezone.now() - timedelta(days=days)

    qs = qs.filter(created_at__gte=since)

    if filters.get('department'):
        qs = qs.filter(assigned_department=filters['department'])
    if filters.get('batch'):
        qs = qs.filter(student__batch_year=filters['batch'])
    if filters.get('type'):
        qs = qs.filter(ticket_type=filters['type'])
    if filters.get('priority'):
        qs = qs.filter(priority=filters['priority'])
    if filters.get('status'):
        qs = qs.filter(status=filters['status'])
    # if filters.get('authority'):
    #     qs = qs.filter(assigned_to__username=filters['authority'])
    if filters.get('authority'):
        authority = User.objects.filter(
            username=filters['authority']
        ).first()

        if authority:
            qs = qs.filter(
                Q(assigned_to=authority)
                | Q(
                    step_executions__actor=authority,
                )
                | Q(
                    step_executions__workflow_step__specific_user_id=authority.id,
                )
            ).distinct()
        else:
            qs = qs.none()
    if filters.get('hostel'):
        qs = qs.filter(student__hostel_block=filters['hostel'])

    return qs


# =====================================================================
# KPI Tiles
# =====================================================================
def compute_kpis(qs):
    """Return the 7 KPI values."""
    now = timezone.now()
    last_30d = now - timedelta(days=30)

    open_qs = qs.filter(status__in=['pending', 'in_progress'])

    # 1. Open Requests
    open_requests = open_qs.count()

    # 2. Critical / Overdue
    critical_overdue = sum(1 for t in open_qs if t.ageing_color == 'red')

    # 3. Avg Resolution Time (last 30d)
    resolved_recent = qs.filter(
        status='resolved',
        resolved_at__gte=last_30d,
        resolved_at__isnull=False,
    )
    if resolved_recent.exists():
        durations = [
            (t.resolved_at - t.created_at).total_seconds() / 3600
            for t in resolved_recent
        ]
        avg_resolution = round(sum(durations) / len(durations), 1)
    else:
        avg_resolution = 0.0

    # 4. SLA Compliance (% resolved within green threshold)
    total_resolved = qs.filter(status='resolved').count()
    compliant = 0
    for t in qs.filter(status='resolved', resolved_at__isnull=False):
        sla = ConfigService.sla_hours_for(t.ticket_type, t.priority)
        if (t.resolved_at - t.created_at).total_seconds() / 3600 <= sla.get('green', 24):
            compliant += 1
    sla_compliance = round((compliant / total_resolved) * 100, 1) if total_resolved else 100.0

    # 5. Attendance Risk
    total_students = User.objects.filter(role='student').count()
    at_risk = 0
    for s in User.objects.filter(role='student'):
        recs = AttendanceRecord.objects.filter(student=s)
        total_held = sum(r.total_classes for r in recs)
        if total_held == 0:
            continue
        total_attended = sum(r.attended_classes for r in recs)
        if total_attended / total_held < 0.75:
            at_risk += 1
    attendance_risk_pct = round((at_risk / total_students) * 100, 1) if total_students else 0.0

    # 6. Notice Reach
    notices = Notice.objects.filter(is_published=True)[:20]
    if notices:
        total_targeted = sum(n.total_targeted() for n in notices)
        total_read = sum(n.read_count() for n in notices)
        notice_reach = round((total_read / total_targeted) * 100, 1) if total_targeted else 0.0
    else:
        notice_reach = 0.0

    # 7. Unresolved Complaints
    unresolved_complaints = qs.filter(
        ticket_type='complaint',
        status__in=['pending', 'in_progress'],
    ).count()

    return {
        'open_requests': open_requests,
        'critical_overdue': critical_overdue,
        'avg_resolution_hours': avg_resolution,
        'sla_compliance': sla_compliance,
        'attendance_risk_pct': attendance_risk_pct,
        'attendance_risk_count': at_risk,
        'notice_reach': notice_reach,
        'unresolved_complaints': unresolved_complaints,
    }


# =====================================================================
# Requests by Type (bar chart)
# =====================================================================
def requests_by_type(qs):
    """Return list of {type, count, label} ordered by count."""
    rows = (
        qs.values('ticket_type')
        .annotate(c=Count('id'))
        .order_by('-c')
    )
    labels = dict(ConfigService.ticket_type_choices())
    return [
        {
            'type': r['ticket_type'],
            'count': r['c'],
            'label': labels.get(r['ticket_type'], r['ticket_type']),
        }
        for r in rows
    ]


# =====================================================================
# Request Volume Trend (line chart, 30 days)
# =====================================================================
def request_volume_trend(qs, days=30):
    """Return daily submitted/approved/rejected/resolved counts."""
    from django.db.models.functions import TruncDate

    now = timezone.now().date()
    start = now - timedelta(days=days - 1)

    trend = {
        start + timedelta(days=i): {
            'submitted': 0,
            'approved': 0,
            'rejected': 0,
            'resolved': 0,
        }
        for i in range(days)
    }

    # Submitted
    for row in (
        qs.filter(created_at__date__gte=start)
        .annotate(d=TruncDate('created_at'))
        .values('d')
        .annotate(c=Count('id'))
    ):
        if row['d'] in trend:
            trend[row['d']]['submitted'] = row['c']

    # Resolved
    for row in (
        qs.filter(
            resolved_at__date__gte=start,
            resolved_at__isnull=False,
        )
        .annotate(d=TruncDate('resolved_at'))
        .values('d')
        .annotate(c=Count('id'))
    ):
        if row['d'] in trend:
            trend[row['d']]['resolved'] = row['c']

    # Approved via workflow steps
    for row in (
        TicketStepExecution.objects
        .filter(
            ticket__in=qs,
            status='approved',
            acted_at__date__gte=start,
        )
        .annotate(d=TruncDate('acted_at'))
        .values('d')
        .annotate(c=Count('id'))
    ):
        if row['d'] in trend:
            trend[row['d']]['approved'] = row['c']

    # Rejected via workflow steps
    for row in (
        TicketStepExecution.objects
        .filter(
            ticket__in=qs,
            status='rejected',
            acted_at__date__gte=start,
        )
        .annotate(d=TruncDate('acted_at'))
        .values('d')
        .annotate(c=Count('id'))
    ):
        if row['d'] in trend:
            trend[row['d']]['rejected'] = row['c']

    return [
        {
            'date': d.strftime('%d %b'),
            **counts,
        }
        for d, counts in sorted(trend.items())
    ]


# =====================================================================
# Department Performance table
# =====================================================================
def department_performance(qs):
    """Return per-department stats."""
    rows = (
        qs.values('assigned_department')
        .annotate(
            total=Count('id'),
            pending=Count('id', filter=Q(status__in=['pending', 'in_progress'])),
        )
        .order_by('-total')
    )

    result = []
    for r in rows:
        dept_code = r['assigned_department'] or 'unassigned'
        dept = ConfigService.department_by_code(dept_code)
        dept_tickets = qs.filter(assigned_department=dept_code)

        # Avg resolution
        resolved = dept_tickets.filter(status='resolved', resolved_at__isnull=False)
        if resolved.exists():
            durations = [(t.resolved_at - t.created_at).total_seconds() / 3600 for t in resolved]
            avg_hours = round(sum(durations) / len(durations), 1)
        else:
            avg_hours = 0.0

        # SLA compliance
        compliant = 0
        for t in resolved:
            sla = ConfigService.sla_hours_for(t.ticket_type, t.priority)
            if (t.resolved_at - t.created_at).total_seconds() / 3600 <= sla.get('green', 24):
                compliant += 1
        sla_pct = round((compliant / resolved.count()) * 100, 1) if resolved.exists() else 100.0

        result.append({
            'code': dept_code,
            'display': dept.name if dept else dept_code.title(),
            'total': r['total'],
            'pending': r['pending'],
            'resolved': resolved.count(),
            'avg_resolution': avg_hours,
            'sla_compliance': sla_pct
        })

    return result


# =====================================================================
# Ageing buckets (heatmap)
# =====================================================================
def ageing_buckets(qs):
    """Return ageing distribution for open tickets."""
    buckets = {
        'fresh':    {'label': 'Fresh (<24h)', 'count': 0, 'color': 'green'},
        'warning':  {'label': 'Watch (24-48h)', 'count': 0, 'color': 'yellow'},
        'critical': {'label': 'Critical (48-72h)', 'count': 0, 'color': 'orange'},
        'overdue':  {'label': 'Overdue (72h+)', 'count': 0, 'color': 'red'},
    }
    for t in qs.filter(status__in=['pending', 'in_progress']):
        color = t.ageing_color
        key = {'green': 'fresh', 'yellow': 'warning', 'orange': 'critical', 'red': 'overdue'}.get(color, 'fresh')
        buckets[key]['count'] += 1
    return buckets


# =====================================================================
# Workflow Bottleneck Analysis
# =====================================================================
def workflow_bottlenecks(qs):
    """
    For each workflow step role, compute:
      - pending count
      - avg wait time (hours since step pending)
    """
    pending_steps = (
        TicketStepExecution.objects
        .filter(status='pending', ticket__in=qs)
        .select_related('workflow_step')
    )

    by_stage = defaultdict(lambda: {'pending': 0, 'total_wait_hours': 0.0})
    now = timezone.now()

    for s in pending_steps:
        role = s.workflow_step.role_required or 'any_admin'
        wait_hours = (now - s.created_at).total_seconds() / 3600
        by_stage[role]['pending'] += 1
        by_stage[role]['total_wait_hours'] += wait_hours

    result = []
    # Hierarchy order
    order = ['asst_prof', 'lab_asst', 'teacher', 'warden', 'hod', 'dean', 'ao', 'principal', 'director', 'chairman']
    for role in order:
        if role not in by_stage:
            continue
        stats = by_stage[role]
        result.append({
            'stage': role.replace('_', ' ').title(),
            'role': role,
            'pending': stats['pending'],
            'avg_wait_hours': round(stats['total_wait_hours'] / stats['pending'], 1) if stats['pending'] else 0,
        })

    # Include any roles not in our order list
    for role, stats in by_stage.items():
        if role not in order:
            result.append({
                'stage': role.replace('_', ' ').title(),
                'role': role,
                'pending': stats['pending'],
                'avg_wait_hours': round(stats['total_wait_hours'] / stats['pending'], 1) if stats['pending'] else 0,
            })

    return result


# =====================================================================
# Academic Risk
# =====================================================================
def academic_risk(batch=None):
    """Return attendance risk stats."""
    students = User.objects.filter(role='student')
    if batch:
        students = students.filter(batch_year=batch)
    total = students.count()
    below_75 = 0
    below_65 = 0

    for s in students:
        recs = AttendanceRecord.objects.filter(student=s)
        total_held = sum(r.total_classes for r in recs)
        if total_held == 0:
            continue
        attended = sum(r.attended_classes for r in recs)
        pct = (attended / total_held) * 100
        if pct < 65:
            below_65 += 1
        elif pct < 75:
            below_75 += 1

    # By batch
    by_batch = []
    for batch in sorted(set(students.values_list('batch_year', flat=True))):
        if not batch:
            continue
        batch_students = students.filter(batch_year=batch)
        batch_risk = 0
        for s in batch_students:
            recs = AttendanceRecord.objects.filter(student=s)
            total_held = sum(r.total_classes for r in recs)
            if total_held > 0:
                attended = sum(r.attended_classes for r in recs)
                if (attended / total_held) < 0.75:
                    batch_risk += 1
        by_batch.append({'batch': batch, 'at_risk': batch_risk, 'total': batch_students.count()})

    # By department
    by_dept = []
    for dept in ConfigService.departments():
        dept_students = students.filter(department=dept.code)
        if not dept_students.exists():
            continue
        dept_risk = 0
        for s in dept_students:
            recs = AttendanceRecord.objects.filter(student=s)
            total_held = sum(r.total_classes for r in recs)
            if total_held > 0:
                attended = sum(r.attended_classes for r in recs)
                if (attended / total_held) < 0.75:
                    dept_risk += 1
        by_dept.append({
            'code': dept.code,
            'display': dept.name,
            'at_risk': dept_risk,
            'total': dept_students.count(),
        })

    return {
        'total_monitored': total,
        'below_75': below_75,
        'below_65': below_65,
        'recovery_plans': below_75 + below_65,
        'by_batch': by_batch,
        'by_dept': by_dept,
    }


# =====================================================================
# Complaint Intelligence
# =====================================================================
def complaint_intelligence(qs):
    """Recurring issues + complaint categories."""
    complaints = qs.filter(ticket_type='complaint')

    # Categories
    categories = dict(Counter(
        ConfigService.department_by_code(t.assigned_department).name
        if t.assigned_department and ConfigService.department_by_code(t.assigned_department)
        else 'Other'
        for t in complaints
    ))

    # Recurring issues (department with 3+)
    recurring_rows = (
        complaints.values('assigned_department')
        .annotate(c=Count('id'))
        .filter(c__gte=3)
        .order_by('-c')[:5]
    )

    recurring = []
    for r in recurring_rows:
        dept = ConfigService.department_by_code(r['assigned_department'])
        # By block
        blocks = dict(Counter(
            t.student.hostel_block
            for t in complaints.filter(assigned_department=r['assigned_department'])
            if t.student.hostel_block and t.student.hostel_block != 'DAY'
        ))
        recurring.append({
            'department': dept.name if dept else r['assigned_department'],
            'count': r['c'],
            'blocks': blocks,
        })

    return {
        'total': complaints.count(),
        'categories': [{'name': k, 'count': v} for k, v in
                       sorted(categories.items(), key=lambda x: -x[1])],
        'recurring': recurring,
    }


# =====================================================================
# Notice Intelligence
# =====================================================================
def notice_intelligence():
    """Notice reach + engagement."""
    notices = Notice.objects.filter(is_published=True)

    total_published = notices.count()
    total_targeted = sum(n.total_targeted() for n in notices)
    total_read = sum(n.read_count() for n in notices)
    unread = total_targeted - total_read

    # By priority
    by_priority = defaultdict(lambda: {'published': 0, 'targeted': 0, 'read': 0})
    for n in notices:
        by_priority[n.ai_priority]['published'] += 1
        by_priority[n.ai_priority]['targeted'] += n.total_targeted()
        by_priority[n.ai_priority]['read'] += n.read_count()

    priority_stats = []
    for prio, stats in by_priority.items():
        pct = (stats['read'] / stats['targeted']) * 100 if stats['targeted'] else 0
        priority_stats.append({
            'priority': prio,
            'published': stats['published'],
            'read_pct': round(pct, 1),
        })

    return {
        'published': total_published,
        'targeted': total_targeted,
        'read': total_read,
        'unread': unread,
        'read_pct': round((total_read / total_targeted) * 100, 1) if total_targeted else 0,
        'by_priority': priority_stats,
    }


# =====================================================================
# Feedback Intelligence (AI-powered)
# =====================================================================
def feedback_intelligence():
    """Student sentiment + top themes + emerging concerns."""
    feedbacks = Feedback.objects.all()

    total = feedbacks.count()
    if total == 0:
        return {
            'total': 0,
            'positive_pct': 0,
            'neutral_pct': 0,
            'negative_pct': 0,
            'themes': [],
            'emerging': [],
        }

    # Sentiment (based on rating)
    positive = feedbacks.filter(rating__gte=4).count()
    neutral = feedbacks.filter(rating=3).count()
    negative = feedbacks.filter(rating__lte=2).count()

    # Themes (by category)
    themes = []
    for row in feedbacks.values('category').annotate(c=Count('id')).order_by('-c'):
        label = dict(Feedback._meta.get_field('category').choices).get(
            row['category'], row['category'])
        themes.append({
            'name': label,
            'count': row['c'],
            'pct': round((row['c'] / total) * 100, 1),
        })

    # Emerging concerns (categories with avg rating <= 2)
    emerging = []
    for row in feedbacks.values('category').annotate(avg=Avg('rating'), c=Count('id')):
        if row['avg'] <= 2.5 and row['c'] >= 2:
            label = dict(Feedback._meta.get_field('category').choices).get(
                row['category'], row['category'])
            emerging.append({
                'name': label,
                'avg_rating': round(row['avg'], 1),
                'count': row['c'],
            })

    return {
        'total': total,
        'positive_pct': round((positive / total) * 100, 1),
        'neutral_pct': round((neutral / total) * 100, 1),
        'negative_pct': round((negative / total) * 100, 1),
        'themes': themes,
        'emerging': emerging,
    }