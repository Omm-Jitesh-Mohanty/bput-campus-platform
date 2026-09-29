"""
Rule-based staffing and operations recommendations.
"""
from .forecast import forecast_by_department
from .health import compute_department_health


def generate_recommendations():
    """
    Return list of {priority, title, detail, action}.
    """
    recs = []

    # 1. Based on health scores
    for d in compute_department_health():
        if d['status'] == 'critical':
            recs.append({
                'priority': 'high',
                'title': f"Immediate attention needed: {d['display']}",
                'detail': (
                    f"Health score {d['score']}/100. "
                    f"{d['breakdown']['open']} open tickets, "
                    f"{d['breakdown']['red_aging']} are overdue."
                ),
                'action': f"Assign additional staff to {d['display']}.",
                'icon': '🚨',
            })
        elif d['status'] == 'at_risk':
            recs.append({
                'priority': 'medium',
                'title': f"Watch {d['display']}",
                'detail': (
                    f"Health score {d['score']}/100. "
                    f"{d['breakdown']['red_aging']} overdue tickets."
                ),
                'action': f"Review {d['display']} backlog this week.",
                'icon': '⚠️',
            })

    # 2. Based on volume forecast
    forecasts = forecast_by_department()
    for code, f in forecasts.items():
        if f['slope'] > 1.0:  # daily increase > 1
            recs.append({
                'priority': 'medium',
                'title': f"Rising load in {f['department']}",
                'detail': (
                    f"Trend: +{f['slope']}/day. "
                    f"Next week forecast: {f['week_forecast']} tickets."
                ),
                'action': f"Consider preemptive staffing for {f['department']}.",
                'icon': '📈',
            })

    return recs[:10]  # cap