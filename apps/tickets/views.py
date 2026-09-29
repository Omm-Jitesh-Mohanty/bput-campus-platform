from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from apps.core.services import ConfigService
from apps.notifications.presence import is_online
from .models import CampusTicket, TicketComment
from .services import create_ticket, resolve_ticket, confirm_resolution


@login_required
def submit_ticket(request):
    """
    Unified ticket creation with dynamic form fields.
    Form fields are driven by TicketType.dynamic_schema.
    """
    from apps.core.services import ConfigService
    from apps.core.form_schema import extract_dynamic_data, prepare_fields_for_render

    if request.user.is_admin_role():
        messages.warning(request, "Admins cannot submit tickets as students.")
        return redirect('dashboard:admin_home')

    # Determine which ticket type we're on (GET param or POST)
    ticket_type_code = (
        request.POST.get('ticket_type')
        or request.GET.get('type')
        or ConfigService.ticket_types()[0].code
        if ConfigService.ticket_types()
        else 'complaint'
    )

    ticket_types = ConfigService.ticket_types()
    selected_type = (
        ConfigService.ticket_type_by_code(ticket_type_code)
        or (ticket_types[0] if ticket_types else None)
    )

    if not selected_type:
        messages.error(request, "No ticket types configured. Contact admin.")
        return redirect('dashboard:student_home')

    # Prepare dynamic fields for rendering
    schema = selected_type.dynamic_schema or {}
    dynamic_fields = prepare_fields_for_render(schema)

    if request.method == 'POST':
        raw_input = request.POST.get('raw_input', '').strip()
        attachment = request.FILES.get('attachment')

        dynamic_data, errors = extract_dynamic_data(
            schema,
            request.POST,
            request.FILES,
        )

        # Base validations
        if not raw_input:
            errors.append("Please describe your issue.")
        elif len(raw_input) < 10:
            errors.append("Please provide at least 10 characters.")

        if errors:
            for e in errors:
                messages.error(request, e)

            return render(
                request,
                'tickets/submit.html',
                {
                    'ticket_types': ticket_types,
                    'selected_type': selected_type,
                    'dynamic_fields': dynamic_fields,
                    'raw_input': raw_input,
                    'dynamic_data': dynamic_data,
                    'posted_data': request.POST,
                },
            )

        # Create
        ticket = create_ticket(
            student=request.user,
            ticket_type=selected_type.code,
            raw_input=raw_input,
            attachment=attachment,
        )

        # ticket.dynamic_data = dynamic_data
        # ticket.save(update_fields=['dynamic_data'])

        # messages.success(
        #     request,
        #     f"Ticket #{ticket.id} submitted."
        # )

        ticket.dynamic_data = dynamic_data
        ticket.save(update_fields=['dynamic_data'])

        from apps.workflows.engine import WorkflowEngine

        WorkflowEngine.attach_workflow(ticket)

        messages.success(
            request,
            f"Ticket #{ticket.id} submitted."
        )

        return redirect(
            'tickets:detail',
            pk=ticket.id,
        )

    return render(
        request,
        'tickets/submit.html',
        {
            'ticket_types': ticket_types,
            'selected_type': selected_type,
            'dynamic_fields': dynamic_fields,
        },
    )


@login_required
def my_tickets(request):
    """
    List of tickets.
    - Students → only their own
    - Admins → full queue with filters
    """
    from .filters import apply_filters, active_filters
    from apps.core.constants import TICKET_STATUS_CHOICES

    if request.user.is_admin_role():
        qs = (
            CampusTicket.objects
            .filter(is_deleted=False)
            .order_by('-created_at')
        )

        qs = apply_filters(request, qs)

        context = {
            'tickets': qs[:200],
            'is_admin_view': True,
            'active': active_filters(request),
            'status_choices': TICKET_STATUS_CHOICES,
            'type_choices': ConfigService.ticket_type_choices(),
            'department_choices': ConfigService.department_choices(),
            'priority_choices': ConfigService.priority_choices(),
        }

    else:
        qs = (
            CampusTicket.objects
            .filter(
                student=request.user,
                is_deleted=False,
            )
            .order_by('-created_at')
        )

        context = {
            'tickets': qs,
            'is_admin_view': False,
        }

    return render(
        request,
        'tickets/list.html',
        context,
    )


@login_required
def ticket_detail(request, pk):
    """Detailed view of a ticket — student or admin."""
    ticket = get_object_or_404(
        CampusTicket,
        pk=pk,
    )

    # Permission check
    if request.user.is_student() and ticket.student != request.user:
        messages.error(
            request,
            "You can only view your own tickets.",
        )

        return redirect(
            'tickets:my_tickets'
        )

    # Get comments (filter internal if student)
    comments_qs = ticket.comments.all()

    if request.user.is_student():
        comments_qs = comments_qs.filter(
            is_internal=False
        )

    return render(
        request,
        'tickets/detail.html',
        {
            'ticket': ticket,
            'comments': comments_qs,
            'ticket_owner_online': is_online(ticket.student_id),
        },
    )


@login_required
def confirm_ticket_resolution(request, pk):
    """Student confirms or disputes resolution."""
    ticket = get_object_or_404(
        CampusTicket,
        pk=pk,
        student=request.user,
    )

    if request.method == 'POST':
        fixed = request.POST.get('fixed') == 'yes'

        confirm_resolution(
            ticket,
            fixed,
        )

        if fixed:
            messages.success(
                request,
                f"Thank you! Ticket #{ticket.id} closed.",
            )
        else:
            messages.warning(
                request,
                f"Ticket #{ticket.id} reopened. "
                f"We'll escalate it.",
            )

        return redirect(
            'tickets:detail',
            pk=ticket.id,
        )

    return redirect(
        'tickets:detail',
        pk=ticket.id,
    )


@login_required
def add_comment(request, pk):
    """Add a comment to a ticket."""
    ticket = get_object_or_404(
        CampusTicket,
        pk=pk,
    )

    # Permission
    if request.user.is_student() and ticket.student != request.user:
        return redirect(
            'tickets:my_tickets'
        )

    if request.method == 'POST':
        body = request.POST.get(
            'body',
            '',
        ).strip()

        is_internal = (
            request.POST.get('is_internal') == 'on'
            and request.user.is_admin_role()
        )

        if body:
            comment = TicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                body=body,
                is_internal=is_internal,
            )

            # Broadcast the new comment to connected ticket-detail clients.
            try:
                from apps.notifications.broadcasters import (
                    broadcast_ticket_comment,
                )

                broadcast_ticket_comment(
                    ticket,
                    comment,
                )

            except Exception as e:
                import logging

                logging.getLogger(__name__).exception(
                    f"comment broadcast failed: {e}"
                )

            messages.success(
                request,
                "Comment added.",
            )

    return redirect(
        'tickets:detail',
        pk=ticket.id,
    )


from apps.core.decorators import admin_required


@admin_required
def admin_resolve_ticket(request, pk):
    """
    Admin action on a ticket.
    If a workflow is attached → act on current step.
    If no workflow → direct resolve (legacy).
    """
    from apps.workflows.engine import WorkflowEngine

    ticket = get_object_or_404(
        CampusTicket,
        pk=pk,
    )

    current = WorkflowEngine.current_step(ticket)

    if request.method == 'POST':
        action = request.POST.get(
            'workflow_action',
            'approve',
        )

        note = request.POST.get(
            'resolution_note',
            '',
        ).strip()

        if not note:
            messages.error(
                request,
                "Please write a note.",
            )

            return redirect(
                'tickets:admin_resolve',
                pk=ticket.id,
            )

        # Check permission
        if current and not WorkflowEngine.can_user_act(
            request.user,
            current,
        ):
            messages.error(
                request,
                f"You are not authorized to act on step "
                f"'{current.workflow_step.name}'.",
            )

            return redirect(
                'tickets:detail',
                pk=ticket.id,
            )

        if current:
            # Act on workflow step
            ok = WorkflowEngine.act(
                ticket,
                current,
                request.user,
                action,
                note,
            )

            if ok:
                if action == 'approve':
                    messages.success(
                        request,
                        f"Step '{current.workflow_step.name}' approved.",
                    )

                elif action == 'reject':
                    messages.warning(
                        request,
                        f"Ticket rejected at step "
                        f"'{current.workflow_step.name}'.",
                    )

                elif action == 'skip':
                    messages.info(
                        request,
                        f"Step '{current.workflow_step.name}' skipped.",
                    )

        else:
            # No workflow — direct resolve
            from .services import resolve_ticket

            resolve_ticket(
                ticket,
                request.user,
                note,
            )

            messages.success(
                request,
                f"Ticket #{ticket.id} resolved.",
            )

        return redirect(
            'tickets:detail',
            pk=ticket.id,
        )

    # GET: show AI-suggested reply
    from ai_engine.pipelines import suggest_resolution_reply

    suggestion = suggest_resolution_reply(ticket)

    return render(
        request,
        'tickets/admin_resolve.html',
        {
            'ticket': ticket,
            'suggestion': suggestion,
            'current_step': current,
            'all_steps': WorkflowEngine.all_steps(ticket),
            'can_act': (
                current is None
                or WorkflowEngine.can_user_act(
                    request.user,
                    current,
                )
            ),
        },
    )


@admin_required
def admin_assign_ticket(request, pk):
    """Admin: assign/route a ticket to a specific department or admin."""
    ticket = get_object_or_404(
        CampusTicket,
        pk=pk,
    )

    if request.method == 'POST':
        department = request.POST.get(
            'department',
            '',
        ).strip()

        priority = request.POST.get(
            'priority',
            '',
        ).strip()

        from .services import assign_ticket

        assign_ticket(
            ticket,
            department=department,
            admin_user=request.user,
            priority=priority,
        )

        messages.success(
            request,
            f"Ticket #{ticket.id} assigned.",
        )

        return redirect(
            'tickets:detail',
            pk=ticket.id,
        )

    return render(
        request,
        'tickets/admin_assign.html',
        {
            'ticket': ticket,
            'departments': ConfigService.department_choices(),
            'priorities': ConfigService.priority_choices(),
        },
    )


@admin_required
def kiosk_new_ticket(request):
    """
    Kiosk mode: admin/office staff creates a ticket on behalf of a
    student who has no smartphone.
    """
    from apps.accounts.models import User
    from .services import create_ticket

    students = User.objects.filter(
        role='student',
        has_smartphone=False,
    )

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        ticket_type = request.POST.get(
            'ticket_type',
            'complaint',
        )

        raw_input = request.POST.get(
            'raw_input',
            '',
        ).strip()

        try:
            student = User.objects.get(
                id=student_id,
                role='student',
            )

        except User.DoesNotExist:
            messages.error(
                request,
                "Invalid student.",
            )

            return redirect(
                'tickets:kiosk_new'
            )

        if not raw_input:
            messages.error(
                request,
                "Please describe the issue.",
            )

        else:
            ticket = create_ticket(
                student=student,
                ticket_type=ticket_type,
                raw_input=raw_input,
                subject=f"[Kiosk] {raw_input[:80]}",
            )

            ticket.ai_metadata['source'] = 'kiosk'
            ticket.ai_metadata['entered_by'] = request.user.username

            ticket.save(
                update_fields=['ai_metadata']
            )

            messages.success(
                request,
                f"Ticket #{ticket.id} created for "
                f"{student.get_full_name() or student.username}. "
                f"Print receipt and hand it to the student.",
            )

            return redirect(
                'tickets:kiosk_receipt',
                pk=ticket.id,
            )

    return render(
        request,
        'tickets/kiosk_new.html',
        {
            'students': students,
            'ticket_types': ConfigService.ticket_type_choices(),
        },
    )


@admin_required
def kiosk_receipt(request, pk):
    """Printable receipt for kiosk submissions."""
    ticket = get_object_or_404(
        CampusTicket,
        pk=pk,
    )

    return render(
        request,
        'tickets/kiosk_receipt.html',
        {
            'ticket': ticket,
        },
    )


@login_required
def ticket_type_fields(request, code):
    """Return HTML for the dynamic fields of a given ticket type."""
    from apps.core.services import ConfigService
    from apps.core.form_schema import prepare_fields_for_render

    tt = ConfigService.ticket_type_by_code(code)

    if not tt:
        return HttpResponse(
            '',
            status=404,
        )

    fields = prepare_fields_for_render(
        tt.dynamic_schema or {}
    )

    return render(
        request,
        'tickets/_dynamic_fields.html',
        {
            'selected_type': tt,
            'dynamic_fields': fields,
        },
    )