"""
Analytics views — predictive dashboard for admins.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.cache import cache

from apps.core.permissions import require_perm, Perm

from .analytics import (
    forecast_ticket_volume,
    forecast_by_department,
    detect_anomalies,
    detect_keyword_clusters,
    detect_recurring_issues,
    predict_sla_breaches,
    compute_department_health,
    compute_system_health,
)
from .analytics.recommender import generate_recommendations


# @require_perm(Perm.VIEW_PREDICTIONS)
@require_perm(Perm.VIEW_ANALYTICS)
def analytics_dashboard(request):
    """Advanced predictive analytics dashboard."""

    # Try cache (10 min)
    cache_key = 'analytics_dashboard_v2'
    context = cache.get(cache_key)

    if context is None:
        context = {
            'forecast': forecast_ticket_volume(days_ahead=7),
            'forecast_by_dept': forecast_by_department(days_ahead=7),
            'anomalies': detect_anomalies(),
            'keyword_clusters': detect_keyword_clusters(
                lookback_days=14,
                min_count=2
            ),
            'recurring': detect_recurring_issues(
                lookback_days=14,
                min_count=2
            ),
            'sla_risk': predict_sla_breaches(hours_ahead=24),
            'system_health': compute_system_health(),
            'recommendations': generate_recommendations(),
        }

        cache.set(
            cache_key,
            context,
            timeout=600
        )

    return render(
        request,
        'dashboard/analytics.html',
        context
    )


@login_required
def refresh_analytics(request):
    if not request.user.is_admin_role():
        return redirect('dashboard:student_home')

    cache.delete('analytics_dashboard_v2')

    return redirect('dashboard:analytics')