# from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from apps.core.constants import (
    TICKET_TYPE_CHOICES, ROUTING_DEPARTMENTS,
    TICKET_TYPE_COMPLAINT,
)
from .models import CampusTicket, TicketComment
from .services import create_ticket, resolve_ticket, confirm_resolution


@login_required
def submit_ticket(request):
    """Unified ticket creation form."""
    if request.user.is_admin_role():
        messages.warning(request, "Admins cannot submit tickets as students.")
        return redirect('dashboard:admin_home')

    if request.method == 'POST':
        ticket_type = request.POST.get('ticket_type', 'complaint').strip()
        raw_input = request.POST.get('raw_input', '').strip()

        if not raw_input:
            messages.error(request, "Please describe your issue.")
        elif len(raw_input) < 10:
            messages.error(request, "Please provide at least 10 characters.")
        else:
            attachment = request.FILES.get('attachment')
            ticket = create_ticket(
                student=request.user,
                ticket_type=ticket_type,
                raw_input=raw_input,
                attachment=attachment,
            )
            messages.success(request, f"Ticket #{ticket.id} submitted. "
                                       f"AI is processing it now.")
            return redirect('tickets:detail', pk=ticket.id)

    return render(request, 'tickets/submit.html', {
        'ticket_types': TICKET_TYPE_CHOICES,
    })


@login_required
def my_tickets(request):
    """
    List of tickets.
    - Students → only their own
    - Admins → full queue with filters
    """
    from .filters import apply_filters, active_filters
    from apps.core.constants import (
        TICKET_TYPE_CHOICES, ROUTING_DEPARTMENTS, PRIORITY_CHOICES,
        TICKET_STATUS_CHOICES,
    )

    if request.user.is_admin_role():
        qs = CampusTicket.objects.filter(is_deleted=False).order_by('-created_at')
        qs = apply_filters(request, qs)
        context = {
            'tickets': qs[:200],
            'is_admin_view': True,
            'active': active_filters(request),
            'status_choices': TICKET_STATUS_CHOICES,
            'type_choices': TICKET_TYPE_CHOICES,
            'department_choices': ROUTING_DEPARTMENTS,
            'priority_choices': PRIORITY_CHOICES,
        }
    else:
        qs = CampusTicket.objects.filter(
            student=request.user, is_deleted=False
        ).order_by('-created_at')
        context = {
            'tickets': qs,
            'is_admin_view': False,
        }

    return render(request, 'tickets/list.html', context)


@login_required
def ticket_detail(request, pk):
    """Detailed view of a ticket — student or admin."""
    ticket = get_object_or_404(CampusTicket, pk=pk)

    # Permission check
    if request.user.is_student() and ticket.student != request.user:
        messages.error(request, "You can only view your own tickets.")
        return redirect('tickets:my_tickets')

    # Get comments (filter internal if student)
    comments_qs = ticket.comments.all()
    if request.user.is_student():
        comments_qs = comments_qs.filter(is_internal=False)

    return render(request, 'tickets/detail.html', {
        'ticket': ticket,
        'comments': comments_qs,
    })


@login_required
def confirm_ticket_resolution(request, pk):
    """Student confirms or disputes resolution."""
    ticket = get_object_or_404(CampusTicket, pk=pk, student=request.user)

    if request.method == 'POST':
        fixed = request.POST.get('fixed') == 'yes'
        confirm_resolution(ticket, fixed)
        if fixed:
            messages.success(request, f"Thank you! Ticket #{ticket.id} closed.")
        else:
            messages.warning(request, f"Ticket #{ticket.id} reopened. "
                                       f"We'll escalate it.")
        return redirect('tickets:detail', pk=ticket.id)

    return redirect('tickets:detail', pk=ticket.id)


@login_required
def add_comment(request, pk):
    """Add a comment to a ticket."""
    ticket = get_object_or_404(CampusTicket, pk=pk)

    # Permission
    if request.user.is_student() and ticket.student != request.user:
        return redirect('tickets:my_tickets')

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        is_internal = request.POST.get('is_internal') == 'on' and request.user.is_admin_role()

        if body:
            TicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                body=body,
                is_internal=is_internal,
            )
            messages.success(request, "Comment added.")

    return redirect('tickets:detail', pk=ticket.id)


from apps.core.decorators import admin_required
from .services import resolve_ticket


@admin_required
def admin_resolve_ticket(request, pk):
    """Admin: view AI-suggested reply and resolve the ticket."""
    ticket = get_object_or_404(CampusTicket, pk=pk)

    if request.method == 'POST':
        note = request.POST.get('resolution_note', '').strip()
        if not note:
            messages.error(request, "Please write a resolution note.")
        else:
            resolve_ticket(ticket, request.user, note)
            messages.success(request, f"Ticket #{ticket.id} resolved.")
            return redirect('tickets:detail', pk=ticket.id)

    # Generate AI suggestion
    from ai_engine.pipelines import suggest_resolution_reply
    suggestion = suggest_resolution_reply(ticket)

    return render(request, 'tickets/admin_resolve.html', {
        'ticket': ticket,
        'suggestion': suggestion,
    })


@admin_required
def admin_assign_ticket(request, pk):
    """Admin: assign/route a ticket to a specific department or admin."""
    ticket = get_object_or_404(CampusTicket, pk=pk)

    if request.method == 'POST':
        department = request.POST.get('department', '').strip()
        priority = request.POST.get('priority', '').strip()

        from .services import assign_ticket
        assign_ticket(ticket, department=department, admin_user=request.user,
                      priority=priority)
        messages.success(request, f"Ticket #{ticket.id} assigned.")
        return redirect('tickets:detail', pk=ticket.id)

    from apps.core.constants import ROUTING_DEPARTMENTS, PRIORITY_CHOICES
    return render(request, 'tickets/admin_assign.html', {
        'ticket': ticket,
        'departments': ROUTING_DEPARTMENTS,
        'priorities': PRIORITY_CHOICES,
    })

from apps.core.decorators import admin_required


@admin_required
def kiosk_new_ticket(request):
    """
    Kiosk mode: admin/office staff creates a ticket on behalf of a
    student who has no smartphone.
    """
    from apps.accounts.models import User
    from .services import create_ticket

    students = User.objects.filter(role='student', has_smartphone=False)

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        ticket_type = request.POST.get('ticket_type', 'complaint')
        raw_input = request.POST.get('raw_input', '').strip()

        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            messages.error(request, "Invalid student.")
            return redirect('tickets:kiosk_new')

        if not raw_input:
            messages.error(request, "Please describe the issue.")
        else:
            ticket = create_ticket(
                student=student,
                ticket_type=ticket_type,
                raw_input=raw_input,
                subject=f"[Kiosk] {raw_input[:80]}",
            )
            ticket.ai_metadata['source'] = 'kiosk'
            ticket.ai_metadata['entered_by'] = request.user.username
            ticket.save(update_fields=['ai_metadata'])

            messages.success(
                request,
                f"Ticket #{ticket.id} created for {student.get_full_name() or student.username}. "
                f"Print receipt and hand it to the student."
            )
            return redirect('tickets:kiosk_receipt', pk=ticket.id)

    from apps.core.constants import TICKET_TYPE_CHOICES
    return render(request, 'tickets/kiosk_new.html', {
        'students': students,
        'ticket_types': TICKET_TYPE_CHOICES,
    })


@admin_required
def kiosk_receipt(request, pk):
    """Printable receipt for kiosk submissions."""
    ticket = get_object_or_404(CampusTicket, pk=pk)
    return render(request, 'tickets/kiosk_receipt.html', {'ticket': ticket})