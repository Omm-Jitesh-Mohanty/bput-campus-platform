"""
Ticket volume forecasting.

Uses a hybrid approach:
  - Weighted moving average (recent days weighted higher)
  - Linear trend component
  - Day-of-week seasonality

Output: 7-day forward forecast with confidence intervals.
"""
import logging
from datetime import timedelta, date
from statistics import mean, stdev

from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate

from apps.tickets.models import CampusTicket
from .stats_utils import linear_regression_slope, clamp

logger = logging.getLogger(__name__)


def _daily_counts(model, days_back=30, filters=None, date_field='created_at'):
    """Return list of (date, count) for the last N days, filling gaps with 0."""
    end = timezone.now().date()
    start = end - timedelta(days=days_back - 1)

    qs = model.objects.filter(**{f'{date_field}__date__gte': start,
                                 f'{date_field}__date__lte': end})
    if filters:
        qs = qs.filter(**filters)

    counts = (
        qs.annotate(d=TruncDate(date_field))
          .values('d')
          .annotate(c=Count('id'))
          .order_by('d')
    )
    by_date = {row['d']: row['c'] for row in counts}

    result = []
    current = start
    while current <= end:
        result.append((current, by_date.get(current, 0)))
        current += timedelta(days=1)
    return result


def forecast_ticket_volume(days_ahead=7, history_days=30):
    """
    Return dict with:
      - history: [(date, count), ...]
      - forecast: [(date, count, lower, upper), ...]
      - trend_direction: 'up' | 'down' | 'stable'
      - trend_pct: percent change per day
      - accuracy: rough estimate based on recent variance
    """
    history = _daily_counts(CampusTicket, days_back=history_days)
    values = [c for _, c in history]

    if not values or sum(values) == 0:
        return _empty_forecast(days_ahead)

    # --- Compute components ---
    recent_7 = values[-7:] if len(values) >= 7 else values
    baseline = mean(recent_7) if recent_7 else 0

    # Trend (over last 14 days)
    window = min(14, len(values))
    slope = linear_regression_slope(values[-window:]) if window >= 2 else 0

    # Day-of-week seasonality
    weekday_avg = _weekday_averages(history)
    overall_avg = mean(values) if values else 1

    # --- Forecast forward ---
    forecast = []
    last_date = history[-1][0]
    today = timezone.now().date()

    for i in range(1, days_ahead + 1):
        target_date = today + timedelta(days=i)
        weekday = target_date.weekday()

        # Base: baseline + trend
        base = baseline + slope * i

        # Seasonal multiplier
        wd_avg = weekday_avg.get(weekday, overall_avg)
        seasonal_factor = (wd_avg / overall_avg) if overall_avg else 1.0

        prediction = max(0, base * seasonal_factor)

        # Confidence interval from recent variance
        spread = stdev(recent_7) if len(recent_7) > 1 else 1
        lower = max(0, prediction - 1.5 * spread)
        upper = prediction + 1.5 * spread

        forecast.append((
            target_date,
            round(prediction, 1),
            round(lower, 1),
            round(upper, 1),
        ))

    # Trend direction
    if abs(slope) < 0.15:
        trend_direction = 'stable'
    elif slope > 0:
        trend_direction = 'up'
    else:
        trend_direction = 'down'

    trend_pct = round((slope / baseline * 100), 1) if baseline else 0

    return {
        'history': history,
        'forecast': forecast,
        'trend_direction': trend_direction,
        'trend_pct': trend_pct,
        'baseline_daily': round(baseline, 1),
        'total_forecast_week': round(sum(f[1] for f in forecast), 0),
        'accuracy': _estimate_accuracy(values),
    }


def _weekday_averages(history):
    """Average count per weekday (0=Mon .. 6=Sun)."""
    buckets = {i: [] for i in range(7)}
    for d, c in history:
        buckets[d.weekday()].append(c)
    return {k: mean(v) if v else 0 for k, v in buckets.items()}


def _estimate_accuracy(values):
    """
    Rough accuracy based on coefficient of variation.
    Low variance → high accuracy.
    """
    if len(values) < 3:
        return 0.5
    m = mean(values)
    if m == 0:
        return 0.5
    cv = stdev(values) / m
    # CV of 0 → 95%, CV of 1 → 50%, CV of 2+ → 30%
    return round(clamp(0.95 - cv * 0.22, 0.3, 0.95), 2)


def _empty_forecast(days_ahead):
    today = timezone.now().date()
    forecast = [
        (today + timedelta(days=i), 0, 0, 0)
        for i in range(1, days_ahead + 1)
    ]
    return {
        'history': [],
        'forecast': forecast,
        'trend_direction': 'stable',
        'trend_pct': 0,
        'baseline_daily': 0,
        'total_forecast_week': 0,
        'accuracy': 0.5,
    }


def forecast_by_department(days_ahead=7):
    """Forecast per department. Returns dict: {dept_code: forecast_dict}."""
    from apps.core.services import ConfigService

    result = {}
    for dept in ConfigService.departments(active_only=True):
        # Count tickets assigned to this dept
        history = _daily_counts(
            CampusTicket, days_back=30,
            filters={'assigned_department': dept.code}
        )
        values = [c for _, c in history]
        if sum(values) < 3:
            continue   # not enough data

        # Simplified per-dept forecast
        recent = values[-7:] if len(values) >= 7 else values
        baseline = mean(recent)
        slope = linear_regression_slope(values[-14:]) if len(values) >= 5 else 0

        week_total = max(0, (baseline + slope * 3.5) * 7)
        result[dept.code] = {
            # 'department': dept.display_name,
            'department': str(dept),
            'baseline_daily': round(baseline, 1),
            'week_forecast': round(week_total, 0),
            'slope': round(slope, 2),
        }
    return result