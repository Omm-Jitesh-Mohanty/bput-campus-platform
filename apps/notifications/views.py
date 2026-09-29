# from django.shortcuts import render

# Create your views here.

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.templatetags.campus_extras import short_time_ago
from .models import Notification


@login_required
def notification_list(request):
    """Full-page list of notifications."""
    notifications = request.user.notifications.all()[:100]
    return render(request, 'notifications/list.html', {
        'notifications': notifications
    })


@login_required
def recent_json(request):
    """Return recent notifications as JSON (for the bell dropdown)."""
    qs = request.user.notifications.all()[:8]
    items = []
    for n in qs:
        items.append({
            'id': n.id,
            'title': n.title,
            'body': n.body,
            'icon': n.icon,
            'is_read': n.is_read,
            'link_url': n.link_url,
            'time_ago': short_time_ago(n.created_at),
        })
    return JsonResponse({
        'notifications': items,
        'unread_count': request.user.notifications.filter(is_read=False).count(),
    })


@login_required
def unread_count(request):
    return JsonResponse({
        'count': request.user.notifications.filter(is_read=False).count()
    })


@login_required
@require_POST
def mark_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    n.mark_read()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return JsonResponse({'ok': True})