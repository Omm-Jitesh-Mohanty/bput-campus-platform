"""Custom template filters for the campus platform."""
from django import template

register = template.Library()


@register.filter
def percentage_color(pct):
    """Return a CSS class based on attendance percentage."""
    try:
        pct = float(pct)
    except (TypeError, ValueError):
        return 'badge-gray'
    if pct >= 85:
        return 'badge-green'
    if pct >= 75:
        return 'badge-yellow'
    return 'badge-red'


@register.filter
def ageing_badge(color):
    """Map ageing color to a badge class."""
    return f'badge-{color}'


@register.filter
def short_time_ago(dt):
    """Return a friendly time-ago string."""
    from django.utils import timezone
    from datetime import timedelta
    if not dt:
        return ''
    now = timezone.now()
    delta = now - dt
    seconds = delta.total_seconds()

    if seconds < 60:
        return 'just now'
    if seconds < 3600:
        return f'{int(seconds // 60)}m ago'
    if seconds < 86400:
        return f'{int(seconds // 3600)}h ago'
    if delta.days < 30:
        return f'{delta.days}d ago'
    return dt.strftime('%d %b %Y')


@register.filter
def status_badge(status):
    """Return a CSS class based on ticket status."""
    mapping = {
        'pending': 'badge-yellow',
        'in_progress': 'badge-blue',
        'resolved': 'badge-green',
        'reopened': 'badge-red',
        'rejected': 'badge-gray',
    }
    return mapping.get(status, 'badge-gray')


@register.filter
def priority_badge(priority):
    mapping = {
        'low': 'badge-gray',
        'medium': 'badge-blue',
        'high': 'badge-yellow',
        'urgent': 'badge-red',
    }
    return mapping.get(priority, 'badge-gray')


@register.filter
def get_initials(user):
    """Return initials from a user's name."""
    if user.get_full_name():
        parts = user.get_full_name().split()
        return ''.join(p[0].upper() for p in parts[:2])
    return user.username[:2].upper()

@register.filter
def get_item(dictionary, key):
    """Get dict value by key in templates."""
    if dictionary is None:
        return None
    return dictionary.get(key)