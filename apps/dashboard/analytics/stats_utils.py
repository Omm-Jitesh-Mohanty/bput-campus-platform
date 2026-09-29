"""
Statistical primitives used across analytics modules.
Pure Python, no external dependencies.
"""
import math
from statistics import mean, stdev, median
from typing import List, Optional


def moving_average(values: List[float], window: int = 7) -> List[float]:
    """Simple moving average. Returns list of same length (padded with None at start)."""
    if not values:
        return []
    if window <= 1:
        return list(values)

    result = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(None)
        else:
            result.append(mean(values[i - window + 1:i + 1]))
    return result


def exponential_moving_average(values: List[float], alpha: float = 0.3) -> List[float]:
    """EMA with smoothing factor alpha (0 < alpha ≤ 1)."""
    if not values:
        return []
    ema = [values[0]]
    for v in values[1:]:
        ema.append(alpha * v + (1 - alpha) * ema[-1])
    return ema


def linear_regression_slope(values: List[float]) -> float:
    """Return slope of best-fit line (y = mx + b). Positive = upward trend."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = mean(values)
    num = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def z_score(value: float, history: List[float]) -> float:
    """How many std devs is `value` from the mean of `history`?"""
    if len(history) < 3:
        return 0.0
    m = mean(history)
    s = stdev(history) if len(history) > 1 else 0
    if s == 0:
        return 0.0
    return (value - m) / s


def percentile(values: List[float], p: float) -> float:
    """Return the p-th percentile (0-100) of values."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_v[int(k)]
    return sorted_v[f] * (c - k) + sorted_v[c] * (k - f)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))