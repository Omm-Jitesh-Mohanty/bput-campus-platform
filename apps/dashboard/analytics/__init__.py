# """Advanced analytics: forecasting, anomaly detection, health scoring."""
# from .forecast import forecast_ticket_volume, forecast_by_department
# from .anomaly import detect_anomalies, detect_recurring_issues
# from .sla_predictor import predict_sla_breaches
# from .health import compute_department_health, compute_system_health

# __all__ = [
#     'forecast_ticket_volume',
#     'forecast_by_department',
#     'detect_anomalies',
#     'detect_recurring_issues',
#     'predict_sla_breaches',
#     'compute_department_health',
#     'compute_system_health',
# ]

"""
Advanced analytics: forecasting, anomaly detection, health scoring.
"""

from .forecast import (
    forecast_ticket_volume,
    forecast_by_department,
)

from .anomaly import (
    detect_anomalies,
    detect_recurring_issues,
    detect_keyword_clusters,
)

from .sla_predictor import (
    predict_sla_breaches,
)

from .health import (
    compute_department_health,
    compute_system_health,
)

__all__ = [
    'forecast_ticket_volume',
    'forecast_by_department',
    'detect_anomalies',
    'detect_recurring_issues',
    'detect_keyword_clusters',
    'predict_sla_breaches',
    'compute_department_health',
    'compute_system_health',
]