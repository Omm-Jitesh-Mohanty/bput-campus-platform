from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.decorators import admin_required
from apps.core.permissions import require_perm, Perm
from .models import EmergencyContact, EmergencyAlert
from .engine import trigger_alert, acknowledge_alert, resolve_alert


@require_perm(Perm.TRIGGER_SOS)
def sos_home(request):
    """Student's SOS screen."""
    if request.user.is_admin_role():
        return redirect('emergency:admin_list')

    contacts = EmergencyContact.objects.filter(
        user=request.user
    ).order_by('priority')

    recent_alerts = EmergencyAlert.objects.filter(
        user=request.user
    )[:5]

    return render(request, 'emergency/sos_home.html', {
        'contacts': contacts,
        'recent_alerts': recent_alerts,
    })


@require_perm(Perm.TRIGGER_SOS)
@require_POST
def trigger_sos(request):
    """Big red button action."""
    if request.user.is_admin_role():
        return redirect('emergency:admin_list')

    trigger_type = request.POST.get(
        'trigger_type',
        'sos_button'
    )

    reason = request.POST.get(
        'reason',
        ''
    ).strip()

    alert = trigger_alert(
        user=request.user,
        trigger_type=trigger_type,
        reason=reason,
    )

    messages.warning(
        request,
        f"🚨 Emergency alert #{alert.id} triggered. "
        f"Calling your contacts now. Stay where you are."
    )

    return redirect(
        'emergency:alert_detail',
        pk=alert.id
    )


@login_required
def alert_detail(request, pk):
    alert = get_object_or_404(
        EmergencyAlert,
        pk=pk
    )

    # Access: owner, or admins who can see
    if (
        not request.user.is_admin_role()
        and alert.user_id != request.user.id
    ):
        return redirect('accounts:home')

    return render(
        request,
        'emergency/alert_detail.html',
        {'alert': alert}
    )


@require_perm(Perm.MANAGE_OWN_CONTACTS)
def contact_manage(request):
    """Manage emergency contacts."""
    if request.user.is_admin_role():
        return redirect('emergency:admin_list')

    contacts = EmergencyContact.objects.filter(
        user=request.user
    ).order_by('priority')

    if request.method == 'POST':
        name = request.POST.get(
            'name',
            ''
        ).strip()

        phone = request.POST.get(
            'phone',
            ''
        ).strip()

        relation = request.POST.get(
            'relation',
            'other'
        )

        priority = int(
            request.POST.get(
                'priority',
                1
            )
        )

        if name and phone:
            EmergencyContact.objects.create(
                user=request.user,
                name=name,
                phone=phone,
                relation=relation,
                priority=priority,
            )

            messages.success(
                request,
                f"Added {name} as emergency contact."
            )

            return redirect(
                'emergency:contacts'
            )

    from .models import EmergencyContact as EC

    return render(
        request,
        'emergency/contacts.html',
        {
            'contacts': contacts,
            'relations': EC.RELATIONS,
        }
    )


@login_required
@require_POST
def contact_delete(request, pk):
    c = get_object_or_404(
        EmergencyContact,
        pk=pk,
        user=request.user
    )

    c.delete()

    return redirect(
        'emergency:contacts'
    )


@require_perm(Perm.RESPOND_TO_SOS)
def admin_alert_list(request):
    from apps.core.scoping import DataScope

    qs = DataScope.sos_queryset(
        request.user
    ).order_by('-created_at')[:100]

    return render(
        request,
        'emergency/admin_list.html',
        {
            'alerts': qs,
            'active_count': sum(
                1
                for a in qs
                if a.status in (
                    'triggered',
                    'calling'
                )
            ),
        }
    )


@require_perm(Perm.RESPOND_TO_SOS)
@require_POST
def admin_acknowledge(request, pk):
    alert = acknowledge_alert(
        pk,
        request.user,
        request.POST.get(
            'note',
            ''
        )
    )

    if alert:
        messages.success(
            request,
            f"Alert #{alert.id} acknowledged."
        )

    return redirect(
        'emergency:admin_list'
    )


@admin_required
@require_POST
def admin_resolve(request, pk):
    alert = resolve_alert(
        pk,
        request.user,
        request.POST.get(
            'note',
            ''
        )
    )

    if alert:
        messages.success(
            request,
            f"Alert #{alert.id} resolved."
        )

    return redirect(
        'emergency:admin_list'
    )


@csrf_exempt
@require_POST
def twilio_acknowledge(request, alert_id):
    """
    Twilio callback when an emergency contact presses 1.

    This endpoint is intentionally CSRF-exempt because Twilio
    calls it directly from the public internet.
    """

    try:
        alert = EmergencyAlert.objects.get(
            pk=alert_id
        )
    except EmergencyAlert.DoesNotExist:
        return HttpResponse(
            "Alert not found",
            status=404
        )

    if alert.status not in (
        'acknowledged',
        'resolved',
    ):
        alert.status = 'acknowledged'
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = None
        alert.resolution_note = (
            "Acknowledged by emergency contact "
            "using Twilio phone keypad."
        )
        alert.save(
            update_fields=[
                'status',
                'acknowledged_at',
                'acknowledged_by',
                'resolution_note',
                'updated_at',
            ]
        )

    return HttpResponse("Acknowledged")