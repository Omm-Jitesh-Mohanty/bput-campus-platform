"""
Anomaly detection + recurring issue detection.

Anomalies: today's metrics that deviate from recent baseline.
Recurring: patterns of similar complaints that suggest systemic issues.
"""
import logging
from datetime import timedelta
from collections import Counter
from statistics import mean, stdev

from django.utils import timezone
from django.db.models import Count

from apps.tickets.models import CampusTicket
from apps.core.services import ConfigService
from .stats_utils import z_score

logger = logging.getLogger(__name__)


def detect_anomalies():
    """
    Scan for anomalies today vs recent baseline.
    Returns list of alerts sorted by severity.
    """
    alerts = []
    today = timezone.now().date()

    # --- 1. Overall volume anomaly ---
    recent_counts = _daily_counts_last_n(14)
    today_count = recent_counts[-1] if recent_counts else 0
    baseline = recent_counts[:-1] if len(recent_counts) > 1 else []

    if baseline and today_count > 0:
        z = z_score(today_count, baseline)
        if z >= 2.0:
            pct = round((today_count - mean(baseline)) / max(1, mean(baseline)) * 100, 0)
            alerts.append({
                'type': 'volume_spike',
                'severity': 'high' if z >= 3 else 'medium',
                'title': f"Ticket volume {pct}% above baseline",
                'description': (
                    f"Today: {today_count} tickets. Recent average: "
                    f"{round(mean(baseline), 1)}/day ({len(baseline)} day baseline)."
                ),
                'metric': {'today': today_count, 'baseline_avg': round(mean(baseline), 1)},
                'icon': '📈',
            })

    # --- 2. Department spike ---
    dept_anomalies = _department_spike_scan()
    alerts.extend(dept_anomalies)

    # --- 3. Recurring issues ---
    recurring = detect_recurring_issues(lookback_days=14, min_count=3)
    for r in recurring[:5]:
        alerts.append({
            'type': 'recurring_issue',
            'severity': 'medium',
            'title': f"Recurring issue: {r['department_display']}",
            'description': (
                f"{r['count']} similar complaints in last {r['lookback_days']} days. "
                f"Likely systemic — investigate root cause."
            ),
            'metric': r,
            'icon': '🔁',
        })

    # --- 4. SLA breach risk ---
    from .sla_predictor import predict_sla_breaches
    breaches = predict_sla_breaches(hours_ahead=24)
    if breaches['count'] > 0:
        alerts.append({
            'type': 'sla_breach_risk',
            'severity': 'high' if breaches['count'] >= 5 else 'medium',
            'title': f"{breaches['count']} tickets at risk of SLA breach",
            'description': (
                f"At current pace, {breaches['count']} tickets will breach SLA "
                f"in the next 24 hours."
            ),
            'metric': breaches,
            'icon': '⏰',
        })

    # Sort by severity
    order = {'high': 0, 'medium': 1, 'low': 2}
    alerts.sort(key=lambda a: order.get(a['severity'], 3))
    return alerts


def _daily_counts_last_n(n):
    """Return list of daily ticket counts for last N days."""
    from django.db.models.functions import TruncDate

    end = timezone.now().date()
    start = end - timedelta(days=n - 1)

    counts = (
        CampusTicket.objects
        .filter(created_at__date__gte=start, created_at__date__lte=end)
        .annotate(d=TruncDate('created_at'))
        .values('d')
        .annotate(c=Count('id'))
        .order_by('d')
    )
    by_date = {row['d']: row['c'] for row in counts}

    result = []
    current = start
    while current <= end:
        result.append(by_date.get(current, 0))
        current += timedelta(days=1)
    return result


def _department_spike_scan():
    """Detect departments with abnormal volume in last 3 days."""
    alerts = []
    now = timezone.now()

    for dept in ConfigService.departments(active_only=True):
        recent = CampusTicket.objects.filter(
            assigned_department=dept.code,
            created_at__gte=now - timedelta(days=3),
        ).count()

        baseline = CampusTicket.objects.filter(
            assigned_department=dept.code,
            created_at__gte=now - timedelta(days=17),
            created_at__lt=now - timedelta(days=3),
        ).count() / 14.0   # daily average

        expected = baseline * 3   # 3 days

        if baseline >= 1 and recent >= expected * 2 and recent >= 5:
            alerts.append({
                'type': 'department_spike',
                'severity': 'medium',
                'title': f"{dept.name} volume doubled",
                'description': (
                    f"{recent} tickets in last 3 days vs expected ~{round(expected, 0)}."
                ),
                'metric': {'dept': dept.code, 'recent': recent, 'expected': round(expected, 0)},
                'icon': '⚡',
            })
    return alerts


# =====================================================================
# RECURRING ISSUE DETECTION
# =====================================================================

def detect_recurring_issues(lookback_days=14, min_count=3):
    """
    Find departments with ≥ min_count complaints in the lookback window.
    Optionally cluster by keyword signature.
    """
    since = timezone.now() - timedelta(days=lookback_days)
    qs = CampusTicket.objects.filter(
        ticket_type='complaint',
        created_at__gte=since,
        is_deleted=False,
    )

    # Aggregate by department
    dept_counts = (
        qs.values('assigned_department')
          .annotate(c=Count('id'))
          .filter(c__gte=min_count)
          .order_by('-c')
    )

    results = []
    for row in dept_counts:
        code = row['assigned_department'] or 'unassigned'
        dept = ConfigService.department_by_code(code)
        results.append({
            'department': code,
            'department_display': dept.name if dept else code.title(),
            'count': row['c'],
            'lookback_days': lookback_days,
        })
    return results


def detect_keyword_clusters(lookback_days=14, min_count=3):
    """
    Find common keywords in recent complaints — a proxy for root causes.
    Uses naive token frequency from subject + raw_input.
    """
    import re
    from collections import Counter

    since = timezone.now() - timedelta(days=lookback_days)
    qs = CampusTicket.objects.filter(
        ticket_type='complaint',
        created_at__gte=since,
        is_deleted=False,
    )

    stop = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'of', 'and', 'or',
            'in', 'on', 'at', 'to', 'for', 'with', 'this', 'that', 'it',
            'my', 'me', 'i', 'we', 'not', 'no', 'has', 'have', 'from', 'very',
            'room', 'block', 'hostel', 'please', 'kindly', 'since', 'days'}

    counts = Counter()
    for t in qs:
        text = f"{t.subject} {t.raw_input}".lower()
        tokens = re.findall(r'[a-z]{3,}', text)
        for tok in tokens:
            if tok not in stop:
                counts[tok] += 1

    return [
        {'keyword': kw, 'count': c}
        for kw, c in counts.most_common(10)
        if c >= min_count
    ]