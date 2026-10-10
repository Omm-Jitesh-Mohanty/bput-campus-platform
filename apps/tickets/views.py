# from django.shortcuts import render, redirect, get_object_or_404
# from django.http import HttpResponse
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.utils import timezone

# from apps.core.services import ConfigService
# from apps.notifications.presence import is_online
# from .models import CampusTicket, TicketComment
# from .services import create_ticket, resolve_ticket, confirm_resolution


# @login_required
# def submit_ticket(request):
#     """
#     Unified ticket creation with dynamic form fields.
#     Form fields are driven by TicketType.dynamic_schema.
#     """
#     from apps.core.services import ConfigService
#     from apps.core.form_schema import extract_dynamic_data, prepare_fields_for_render

#     if request.user.is_admin_role():
#         messages.warning(request, "Admins cannot submit tickets as students.")
#         return redirect('dashboard:admin_home')

#     # Determine which ticket type we're on (GET param or POST)
#     ticket_type_code = (
#         request.POST.get('ticket_type')
#         or request.GET.get('type')
#         or ConfigService.ticket_types()[0].code
#         if ConfigService.ticket_types()
#         else 'complaint'
#     )

#     ticket_types = ConfigService.ticket_types()
#     selected_type = (
#         ConfigService.ticket_type_by_code(ticket_type_code)
#         or (ticket_types[0] if ticket_types else None)
#     )

#     if not selected_type:
#         messages.error(request, "No ticket types configured. Contact admin.")
#         return redirect('dashboard:student_home')

#     # Prepare dynamic fields for rendering
#     schema = selected_type.dynamic_schema or {}
#     dynamic_fields = prepare_fields_for_render(schema)

#     if request.method == 'POST':
#         raw_input = request.POST.get('raw_input', '').strip()
#         attachment = request.FILES.get('attachment')

#         dynamic_data, errors = extract_dynamic_data(
#             schema,
#             request.POST,
#             request.FILES,
#         )

#         # Base validations
#         if not raw_input:
#             errors.append("Please describe your issue.")
#         elif len(raw_input) < 10:
#             errors.append("Please provide at least 10 characters.")

#         if errors:
#             for e in errors:
#                 messages.error(request, e)

#             return render(
#                 request,
#                 'tickets/submit.html',
#                 {
#                     'ticket_types': ticket_types,
#                     'selected_type': selected_type,
#                     'dynamic_fields': dynamic_fields,
#                     'raw_input': raw_input,
#                     'dynamic_data': dynamic_data,
#                     'posted_data': request.POST,
#                 },
#             )

#         # Create
#         ticket = create_ticket(
#             student=request.user,
#             ticket_type=selected_type.code,
#             raw_input=raw_input,
#             attachment=attachment,
#         )

#         # ticket.dynamic_data = dynamic_data
#         # ticket.save(update_fields=['dynamic_data'])

#         # messages.success(
#         #     request,
#         #     f"Ticket #{ticket.id} submitted."
#         # )

#         ticket.dynamic_data = dynamic_data
#         ticket.save(update_fields=['dynamic_data'])

#         from apps.workflows.engine import WorkflowEngine

#         WorkflowEngine.attach_workflow(ticket)

#         messages.success(
#             request,
#             f"Ticket #{ticket.id} submitted."
#         )

#         return redirect(
#             'tickets:detail',
#             pk=ticket.id,
#         )

#     return render(
#         request,
#         'tickets/submit.html',
#         {
#             'ticket_types': ticket_types,
#             'selected_type': selected_type,
#             'dynamic_fields': dynamic_fields,
#         },
#     )


# @login_required
# def my_tickets(request):
#     """
#     List of tickets.
#     - Students → only their own
#     - Admins → full queue with filters
#     """
#     from .filters import apply_filters, active_filters
#     from apps.core.constants import TICKET_STATUS_CHOICES

#     if request.user.is_admin_role():
#         qs = (
#             CampusTicket.objects
#             .filter(is_deleted=False)
#             .order_by('-created_at')
#         )

#         qs = apply_filters(request, qs)

#         context = {
#             'tickets': qs[:200],
#             'is_admin_view': True,
#             'active': active_filters(request),
#             'status_choices': TICKET_STATUS_CHOICES,
#             'type_choices': ConfigService.ticket_type_choices(),
#             'department_choices': ConfigService.department_choices(),
#             'priority_choices': ConfigService.priority_choices(),
#         }

#     else:
#         qs = (
#             CampusTicket.objects
#             .filter(
#                 student=request.user,
#                 is_deleted=False,
#             )
#             .order_by('-created_at')
#         )

#         context = {
#             'tickets': qs,
#             'is_admin_view': False,
#         }

#     return render(
#         request,
#         'tickets/list.html',
#         context,
#     )


# @login_required
# def ticket_detail(request, pk):
#     """Detailed view of a ticket — student or admin."""
#     ticket = get_object_or_404(
#         CampusTicket,
#         pk=pk,
#     )

#     # Permission check
#     if request.user.is_student() and ticket.student != request.user:
#         messages.error(
#             request,
#             "You can only view your own tickets.",
#         )

#         return redirect(
#             'tickets:my_tickets'
#         )

#     # Get comments (filter internal if student)
#     comments_qs = ticket.comments.all()

#     if request.user.is_student():
#         comments_qs = comments_qs.filter(
#             is_internal=False
#         )

#     return render(
#         request,
#         'tickets/detail.html',
#         {
#             'ticket': ticket,
#             'comments': comments_qs,
#             'ticket_owner_online': is_online(ticket.student_id),
#         },
#     )


# @login_required
# def confirm_ticket_resolution(request, pk):
#     """Student confirms or disputes resolution."""
#     ticket = get_object_or_404(
#         CampusTicket,
#         pk=pk,
#         student=request.user,
#     )

#     if request.method == 'POST':
#         fixed = request.POST.get('fixed') == 'yes'

#         confirm_resolution(
#             ticket,
#             fixed,
#         )

#         if fixed:
#             messages.success(
#                 request,
#                 f"Thank you! Ticket #{ticket.id} closed.",
#             )
#         else:
#             messages.warning(
#                 request,
#                 f"Ticket #{ticket.id} reopened. "
#                 f"We'll escalate it.",
#             )

#         return redirect(
#             'tickets:detail',
#             pk=ticket.id,
#         )

#     return redirect(
#         'tickets:detail',
#         pk=ticket.id,
#     )


# @login_required
# def add_comment(request, pk):
#     """Add a comment to a ticket."""
#     ticket = get_object_or_404(
#         CampusTicket,
#         pk=pk,
#     )

#     # Permission
#     if request.user.is_student() and ticket.student != request.user:
#         return redirect(
#             'tickets:my_tickets'
#         )

#     if request.method == 'POST':
#         body = request.POST.get(
#             'body',
#             '',
#         ).strip()

#         is_internal = (
#             request.POST.get('is_internal') == 'on'
#             and request.user.is_admin_role()
#         )

#         if body:
#             comment = TicketComment.objects.create(
#                 ticket=ticket,
#                 author=request.user,
#                 body=body,
#                 is_internal=is_internal,
#             )

#             # Broadcast the new comment to connected ticket-detail clients.
#             try:
#                 from apps.notifications.broadcasters import (
#                     broadcast_ticket_comment,
#                 )

#                 broadcast_ticket_comment(
#                     ticket,
#                     comment,
#                 )

#             except Exception as e:
#                 import logging

#                 logging.getLogger(__name__).exception(
#                     f"comment broadcast failed: {e}"
#                 )

#             messages.success(
#                 request,
#                 "Comment added.",
#             )

#     return redirect(
#         'tickets:detail',
#         pk=ticket.id,
#     )


# from apps.core.decorators import admin_required


# @admin_required
# def admin_resolve_ticket(request, pk):
#     """
#     Admin action on a ticket.
#     If a workflow is attached → act on current step.
#     If no workflow → direct resolve (legacy).
#     """
#     from apps.workflows.engine import WorkflowEngine

#     ticket = get_object_or_404(
#         CampusTicket,
#         pk=pk,
#     )

#     current = WorkflowEngine.current_step(ticket)

#     if request.method == 'POST':
#         action = request.POST.get(
#             'workflow_action',
#             'approve',
#         )

#         note = request.POST.get(
#             'resolution_note',
#             '',
#         ).strip()

#         if not note:
#             messages.error(
#                 request,
#                 "Please write a note.",
#             )

#             return redirect(
#                 'tickets:admin_resolve',
#                 pk=ticket.id,
#             )

#         # Check permission
#         if current and not WorkflowEngine.can_user_act(
#             request.user,
#             current,
#         ):
#             messages.error(
#                 request,
#                 f"You are not authorized to act on step "
#                 f"'{current.workflow_step.name}'.",
#             )

#             return redirect(
#                 'tickets:detail',
#                 pk=ticket.id,
#             )

#         if current:
#             # Act on workflow step
#             ok = WorkflowEngine.act(
#                 ticket,
#                 current,
#                 request.user,
#                 action,
#                 note,
#             )

#             if ok:
#                 if action == 'approve':
#                     messages.success(
#                         request,
#                         f"Step '{current.workflow_step.name}' approved.",
#                     )

#                 elif action == 'reject':
#                     messages.warning(
#                         request,
#                         f"Ticket rejected at step "
#                         f"'{current.workflow_step.name}'.",
#                     )

#                 elif action == 'skip':
#                     messages.info(
#                         request,
#                         f"Step '{current.workflow_step.name}' skipped.",
#                     )

#         else:
#             # No workflow — direct resolve
#             from .services import resolve_ticket

#             resolve_ticket(
#                 ticket,
#                 request.user,
#                 note,
#             )

#             messages.success(
#                 request,
#                 f"Ticket #{ticket.id} resolved.",
#             )

#         return redirect(
#             'tickets:detail',
#             pk=ticket.id,
#         )

#     # GET: show AI-suggested reply
#     from ai_engine.pipelines import suggest_resolution_reply

#     suggestion = suggest_resolution_reply(ticket)

#     return render(
#         request,
#         'tickets/admin_resolve.html',
#         {
#             'ticket': ticket,
#             'suggestion': suggestion,
#             'current_step': current,
#             'all_steps': WorkflowEngine.all_steps(ticket),
#             'can_act': (
#                 current is None
#                 or WorkflowEngine.can_user_act(
#                     request.user,
#                     current,
#                 )
#             ),
#         },
#     )


# @admin_required
# def admin_assign_ticket(request, pk):
#     """Admin: assign/route a ticket to a specific department or admin."""
#     ticket = get_object_or_404(
#         CampusTicket,
#         pk=pk,
#     )

#     if request.method == 'POST':
#         department = request.POST.get(
#             'department',
#             '',
#         ).strip()

#         priority = request.POST.get(
#             'priority',
#             '',
#         ).strip()

#         from .services import assign_ticket

#         assign_ticket(
#             ticket,
#             department=department,
#             admin_user=request.user,
#             priority=priority,
#         )

#         messages.success(
#             request,
#             f"Ticket #{ticket.id} assigned.",
#         )

#         return redirect(
#             'tickets:detail',
#             pk=ticket.id,
#         )

#     return render(
#         request,
#         'tickets/admin_assign.html',
#         {
#             'ticket': ticket,
#             'departments': ConfigService.department_choices(),
#             'priorities': ConfigService.priority_choices(),
#         },
#     )


# @admin_required
# def kiosk_new_ticket(request):
#     """
#     Kiosk mode: admin/office staff creates a ticket on behalf of a
#     student who has no smartphone.
#     """
#     from apps.accounts.models import User
#     from .services import create_ticket

#     students = User.objects.filter(
#         role='student',
#         has_smartphone=False,
#     )

#     if request.method == 'POST':
#         student_id = request.POST.get('student_id')
#         ticket_type = request.POST.get(
#             'ticket_type',
#             'complaint',
#         )

#         raw_input = request.POST.get(
#             'raw_input',
#             '',
#         ).strip()

#         try:
#             student = User.objects.get(
#                 id=student_id,
#                 role='student',
#             )

#         except User.DoesNotExist:
#             messages.error(
#                 request,
#                 "Invalid student.",
#             )

#             return redirect(
#                 'tickets:kiosk_new'
#             )

#         if not raw_input:
#             messages.error(
#                 request,
#                 "Please describe the issue.",
#             )

#         else:
#             ticket = create_ticket(
#                 student=student,
#                 ticket_type=ticket_type,
#                 raw_input=raw_input,
#                 subject=f"[Kiosk] {raw_input[:80]}",
#             )

#             ticket.ai_metadata['source'] = 'kiosk'
#             ticket.ai_metadata['entered_by'] = request.user.username

#             ticket.save(
#                 update_fields=['ai_metadata']
#             )

#             messages.success(
#                 request,
#                 f"Ticket #{ticket.id} created for "
#                 f"{student.get_full_name() or student.username}. "
#                 f"Print receipt and hand it to the student.",
#             )

#             return redirect(
#                 'tickets:kiosk_receipt',
#                 pk=ticket.id,
#             )

#     return render(
#         request,
#         'tickets/kiosk_new.html',
#         {
#             'students': students,
#             'ticket_types': ConfigService.ticket_type_choices(),
#         },
#     )


# @admin_required
# def kiosk_receipt(request, pk):
#     """Printable receipt for kiosk submissions."""
#     ticket = get_object_or_404(
#         CampusTicket,
#         pk=pk,
#     )

#     return render(
#         request,
#         'tickets/kiosk_receipt.html',
#         {
#             'ticket': ticket,
#         },
#     )


# @login_required
# def ticket_type_fields(request, code):
#     """Return HTML for the dynamic fields of a given ticket type."""
#     from apps.core.services import ConfigService
#     from apps.core.form_schema import prepare_fields_for_render

#     tt = ConfigService.ticket_type_by_code(code)

#     if not tt:
#         return HttpResponse(
#             '',
#             status=404,
#         )

#     fields = prepare_fields_for_render(
#         tt.dynamic_schema or {}
#     )

#     return render(
#         request,
#         'tickets/_dynamic_fields.html',
#         {
#             'selected_type': tt,
#             'dynamic_fields': fields,
#         },
#     )

from django.shortcuts import render, redirect, get_object_or_404

from django.http import HttpResponse, JsonResponse

from django.contrib.auth.decorators import login_required

from django.contrib import messages

from django.utils import timezone



from apps.core.services import ConfigService

from apps.core.scoping import DataScope

from apps.core.permissions import require_perm, require_any_perm, Perm

from apps.notifications.presence import is_online



from .models import CampusTicket, TicketComment

from .services import create_ticket, resolve_ticket, confirm_resolution





@require_perm(Perm.SUBMIT_TICKET)

def submit_ticket(request):

    """

    Unified ticket creation with dynamic form fields.



    Form fields are driven by TicketType.dynamic_schema.

    """



    from apps.core.services import ConfigService

    from apps.core.form_schema import (

        extract_dynamic_data,

        prepare_fields_for_render,

    )



    if request.user.is_admin_role():

        messages.warning(

            request,

            "Admins cannot submit tickets as students.",

        )

        return redirect('dashboard:admin_home')



    # Determine which ticket type we're on (GET param or POST)

    ticket_type_code = (

        request.POST.get('ticket_type')

        or request.GET.get('type')

        or (

            ConfigService.ticket_types()[0].code

            if ConfigService.ticket_types()

            else 'complaint'

        )

    )



    ticket_types = ConfigService.ticket_types()



    selected_type = (

        ConfigService.ticket_type_by_code(ticket_type_code)

        or (ticket_types[0] if ticket_types else None)

    )



    if not selected_type:

        messages.error(

            request,

            "No ticket types configured. Contact admin.",

        )

        return redirect('dashboard:student_home')



    # Prepare dynamic fields for rendering

    schema = selected_type.dynamic_schema or {}

    dynamic_fields = prepare_fields_for_render(schema)



    if request.method == 'POST':

        raw_input = request.POST.get(

            'raw_input',

            '',

        ).strip()



        attachment = request.FILES.get('attachment')



        dynamic_data, errors = extract_dynamic_data(

            schema,

            request.POST,

            request.FILES,

        )



        # Base validations

        if not raw_input:

            errors.append(

                "Please describe your issue."

            )

        elif len(raw_input) < 10:

            errors.append(

                "Please provide at least 10 characters."

            )



        if errors:

            for e in errors:

                messages.error(

                    request,

                    e,

                )



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
            subject=raw_input[:200],
            attachment=attachment,
            enrich=False,
        )

        ticket.dynamic_data = dynamic_data
        ticket.save(update_fields=["dynamic_data", "updated_at"])

        from ai_engine.pipelines import process_new_ticket
        process_new_ticket(ticket, save=True)

        from apps.workflows.engine import WorkflowEngine
        workflow = WorkflowEngine.attach_workflow(ticket)

        if workflow:
            ticket.ai_metadata = {
                **(ticket.ai_metadata or {}),
                "workflow": workflow.code,
            }
            ticket.save(update_fields=["ai_metadata", "updated_at"])

        messages.success(
            request,
            f"Ticket #{ticket.id} submitted.",
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





@require_any_perm(

    Perm.VIEW_OWN_TICKETS,

    Perm.VIEW_TICKET_QUEUE,

)

def my_tickets(request):

    """

    Role-scoped ticket list.

    """



    from .filters import apply_filters, active_filters

    from apps.core.services import ConfigService



    # Scoped base queryset

    qs = DataScope.ticket_queryset(

        request.user

    ).order_by('-created_at')



    if request.user.is_student():

        context = {

            'tickets': qs,

            'is_admin_view': False,

        }

    else:

        qs = apply_filters(

            request,

            qs,

        )



        context = {

            'tickets': qs[:200],

            'is_admin_view': True,

            'active': active_filters(request),

            'status_choices': [

                ('pending', 'Pending'),

                ('in_progress', 'In Progress'),

                ('resolved', 'Resolved'),

                ('reopened', 'Reopened'),

            ],

            'type_choices': ConfigService.ticket_type_choices(),

            'department_choices': ConfigService.department_choices(),

            'priority_choices': ConfigService.priority_choices(),

            'scope_label': request.user.scope_summary(),

        }



    return render(

        request,

        'tickets/list.html',

        context,

    )





@login_required

def queue_router(request):

    """Route to the right queue based on role."""

    if request.user.is_student():

        return redirect('tickets:my_tickets')

    if request.user.role in (

        'principal',

        'director',

        'chairman',

    ):

        return redirect('tickets:all_tickets')

    return redirect('tickets:my_queue')





@require_perm(Perm.VIEW_TICKET_QUEUE)

def my_queue(request):

    """

    Unified queue view for admin-side users.



    Shows ONLY tickets where:

      - The user is the current approver for a pending step, OR

      - The user is assigned to the ticket directly, OR

      - (For principal/dean) All tickets with an actionable state



    Non-actionable tickets are NEVER shown — no "you don't have access"

    errors.

    """



    from apps.workflows.models import TicketStepExecution

    from apps.workflows.engine import WorkflowEngine

    from apps.tickets.filters import apply_filters, active_filters



    # 1. Get all tickets currently awaiting approval from THIS user

    pending_steps = (

        TicketStepExecution.objects

        .filter(status='pending')

        .select_related(

            'ticket',

            'workflow_step',

            'ticket__student',

        )

    )



    my_actionable = []



    for step in pending_steps:

        if not DataScope.can_access_ticket(

            request.user,

            step.ticket,

        ):

            continue



        if WorkflowEngine.can_user_act(

            request.user,

            step,

        ):

            my_actionable.append(

                step.ticket

            )



    # 2. Also include tickets directly assigned to this user

    directly_assigned = (

        DataScope.ticket_queryset(

            request.user

        )

        .filter(

            assigned_to=request.user,

            status__in=[

                'pending',

                'in_progress',

            ],

        )

    )



    # Combine and dedupe

    ticket_ids = (

        set(

            t.id

            for t in my_actionable

        )

        |

        set(

            t.id

            for t in directly_assigned

        )

    )



    qs = (

        CampusTicket.objects

        .filter(id__in=ticket_ids)

        .order_by('-created_at')

    )



    # 3. Apply URL filters

    # search, status, type, priority

    qs = apply_filters(

        request,

        qs,

    )



    context = {

        'tickets': qs,

        'is_admin_view': True,

        'active': active_filters(request),

        'status_choices': [

            ('pending', 'Pending'),

            ('in_progress', 'In Progress'),

            ('resolved', 'Resolved'),

            ('reopened', 'Reopened'),

        ],

        'type_choices': ConfigService.ticket_type_choices(),

        'department_choices': ConfigService.department_choices(),

        'priority_choices': ConfigService.priority_choices(),

        'scope_label': request.user.scope_summary(),

        'queue_count': len(ticket_ids),

    }



    return render(

        request,

        'tickets/queue.html',

        context,

    )





@require_perm(Perm.VIEW_TICKET_QUEUE)

def all_tickets(request):

    """

    Master queue for principal/director/chairman.



    Shows every ticket but still respects filters.

    """



    from apps.tickets.filters import apply_filters, active_filters



    # Top-tier roles see everything

    if request.user.role in (

        'principal',

        'director',

        'chairman',

        'dean',

    ):

        qs = (

            CampusTicket.objects

            .filter(is_deleted=False)

            .order_by('-created_at')

        )

    else:

        # Everyone else uses scoped access

        qs = (

            DataScope.ticket_queryset(

                request.user

            )

            .order_by('-created_at')

        )



    qs = apply_filters(

        request,

        qs,

    )



    context = {

        'tickets': qs[:200],

        'is_admin_view': True,

        'is_master_view': True,

        'active': active_filters(request),

        'status_choices': [

            ('pending', 'Pending'),

            ('in_progress', 'In Progress'),

            ('resolved', 'Resolved'),

            ('reopened', 'Reopened'),

        ],

        'type_choices': ConfigService.ticket_type_choices(),

        'department_choices': ConfigService.department_choices(),

        'priority_choices': ConfigService.priority_choices(),

        'scope_label': request.user.scope_summary(),

    }



    return render(

        request,

        'tickets/queue.html',

        context,

    )





@require_perm(Perm.APPROVE_TICKET_STEP)

def my_approvals(request):

    """

    Tickets awaiting this user's action.



    Kept as a compatibility wrapper for existing URLs.

    """



    return my_queue(request)





@require_perm(Perm.VIEW_TICKET_DETAIL)

def ticket_detail(request, pk):

    """

    Detailed view of a ticket with role-based data scoping.

    """



    ticket = get_object_or_404(

        CampusTicket,

        pk=pk,

    )



    if not DataScope.can_access_ticket(

        request.user,

        ticket,

    ):

        messages.error(

            request,

            "You don't have access to this ticket.",

        )



        # if request.user.is_admin_role():

        #     return redirect(

        #         'dashboard:admin_home'

        #     )



        # return redirect(

        #     'dashboard:student_home'

        # )
        if hasattr(
            request.user,
            'home_redirect',
        ):
            return redirect(
                request.user.home_redirect()
            )

        return redirect('home')



    # Filter internal comments for students

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

        },

    )





@login_required

def confirm_ticket_resolution(request, pk):

    """

    Student confirms or disputes resolution.

    """



    ticket = get_object_or_404(

        CampusTicket,

        pk=pk,

        student=request.user,

    )



    if request.method == 'POST':

        fixed = (

            request.POST.get('fixed') == 'yes'

        )



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





@require_perm(Perm.ADD_TICKET_COMMENT)

def add_comment(request, pk):

    """

    Add a comment to a ticket.

    """



    ticket = get_object_or_404(

        CampusTicket,

        pk=pk,

    )



    # Permission

    if (

        request.user.is_student()

        and ticket.student != request.user

    ):

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



                logging.getLogger(

                    __name__

                ).exception(

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





@require_perm(Perm.APPROVE_TICKET_STEP)

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



    current = WorkflowEngine.current_step(

        ticket

    )



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

        if (

            current

            and not WorkflowEngine.can_user_act(

                request.user,

                current,

            )

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
            acted_step_name = current.workflow_step.name

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

                        # f"Step '{current.workflow_step.name}' approved.",
                        f"✅ Step '{acted_step_name}' approved."

                    )



                elif action == 'reject':

                    messages.warning(

                        request,

                        # f"Ticket rejected at step "

                        # f"'{current.workflow_step.name}'.",
                        f"❌ Ticket rejected at step '{acted_step_name}'."

                    )



                elif action == 'skip':

                    messages.info(

                        request,

                        # f"Step '{current.workflow_step.name}' skipped.",
                        f"⏭ Step '{acted_step_name}' skipped."

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





@require_perm(Perm.ASSIGN_TICKET)

def admin_assign_ticket(request, pk):

    """

    Admin: assign/route a ticket to a specific department or admin.

    """



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





@require_perm(Perm.MANAGE_WORKFLOWS)

def change_ticket_workflow(request, pk):

    """

    Admin override: change the workflow for a ticket.

    """



    ticket = get_object_or_404(

        CampusTicket,

        pk=pk,

    )



    if request.method == 'POST':

        new_wf_code = request.POST.get(

            'workflow_code',

            '',

        )



        from apps.workflows.models import (

            Workflow,

            TicketStepExecution,

        )



        new_wf = Workflow.objects.filter(

            code=new_wf_code,

            is_active=True,

        ).first()



        if not new_wf:

            messages.error(

                request,

                "Invalid workflow.",

            )

        else:

            # Remove existing step executions

            TicketStepExecution.objects.filter(

                ticket=ticket,

            ).delete()



            # Attach new workflow

            from apps.workflows.engine import WorkflowEngine



            WorkflowEngine.attach_workflow(

                ticket

            )



            messages.success(

                request,

                f"Workflow changed to {new_wf.name}.",

            )



            return redirect(

                'tickets:detail',

                pk=ticket.id,

            )



    from apps.workflows.models import Workflow



    return render(

        request,

        'tickets/change_workflow.html',

        {

            'ticket': ticket,

            'workflows': Workflow.objects.filter(

                is_active=True,

            ),

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

        student_id = request.POST.get(

            'student_id'

        )



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

            ticket.ai_metadata['entered_by'] = (

                request.user.username

            )



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

    """

    Printable receipt for kiosk submissions.

    """



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

    """

    Return HTML for the dynamic fields of a given ticket type.

    """



    from apps.core.services import ConfigService

    from apps.core.form_schema import prepare_fields_for_render



    tt = ConfigService.ticket_type_by_code(

        code

    )



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





# temporary: allow students to preview AI-formatted ticket text before submission

# @require_perm(Perm.VIEW_TICKET_DETAIL)
@require_perm(Perm.SUBMIT_TICKET)

def preview_formatted_ticket(request):

    """

    Preview the AI-formatted ticket text before submission.

    """



    if request.method != 'POST':

        return JsonResponse(

            {

                'ok': False,

                'error': 'POST request required.',

            },

            status=405,

        )



    if request.user.is_admin_role():

        return JsonResponse(

            {

                'ok': False,

                'error': 'Administrators cannot submit tickets as students.',

            },

            status=403,

        )



    try:

        import json



        try:

            payload = json.loads(

                request.body or '{}'

            )



        except json.JSONDecodeError:

            return JsonResponse(

                {

                    'ok': False,

                    'error': 'Invalid JSON request.',

                },

                status=400,

            )



        raw_input = str(

            payload.get(

                'raw_input',

                '',

            )

        ).strip()



        ticket_type_code = str(

            payload.get('ticket_type')

            or request.session.get('ticket_type')

            or 'complaint'

        ).strip()



        dynamic_data = payload.get(

            'dynamic_data',

            {},

        )



        if not raw_input:

            return JsonResponse(

                {

                    'ok': False,

                    'error': 'Please provide the issue description.',

                },

                status=400,

            )



        if len(raw_input) < 10:

            return JsonResponse(

                {

                    'ok': False,

                    'error': 'Please provide at least 10 characters.',

                },

                status=400,

            )



        selected_type = (

            ConfigService.ticket_type_by_code(

                ticket_type_code

            )

        )



        if not selected_type:

            ticket_types = ConfigService.ticket_types()



            if ticket_types:

                selected_type = ticket_types[0]

                ticket_type_code = selected_type.code



            else:

                return JsonResponse(

                    {

                        'ok': False,

                        'error': 'No ticket types are configured.',

                    },

                    status=400,

                )



        if not isinstance(

            dynamic_data,

            dict,

        ):

            dynamic_data = {}



        ticket = CampusTicket(

            student=request.user,

            ticket_type=ticket_type_code,

            raw_input=raw_input,

            subject=raw_input[:100],

            dynamic_data=dynamic_data,

        )



        from ai_engine.pipelines.ticket_pipeline import process_new_ticket



        ticket = process_new_ticket(

            ticket,

            save=False,

        )



        formatted_text = (

            ticket.formatted_body

            or raw_input

        )



        ai_metadata = (

            ticket.ai_metadata

            or {}

        )



        formatter_meta = ai_metadata.get(

            'formatter',

            {},

        )



        return JsonResponse(

            {

                'ok': True,

                'draft': formatted_text,

                'source': formatter_meta.get(

                    'source',

                    'fallback',

                ),

                'latency_ms': formatter_meta.get(

                    'latency_ms',

                ),

                'ticket_type': ticket_type_code,

            }

        )



    except Exception as exc:

        import logging



        logging.getLogger(

            __name__

        ).exception(

            "Failed to generate AI preview: %s",

            exc,

        )



        return JsonResponse(

            {

                'ok': False,

                'error': (

                    'Unable to generate the AI application. '

                    'Please try again.'

                ),

            },

            status=500,

        )





# @login_required
@require_perm(Perm.SUBMIT_TICKET)
def confirm_submit_ticket(request):

    """

    Create the final ticket after the student reviews and edits

    the AI draft.

    """



    if request.method != 'POST':

        return HttpResponse(

            'POST request required.',

            status=405,

        )



    if request.user.is_admin_role():

        return HttpResponse(

            'Administrators cannot submit tickets as students.',

            status=403,

        )



    final_text = (

        request.POST.get('final_text')

        or request.POST.get('formatted_text')

        or request.POST.get('raw_input')

        or ''

    ).strip()



    if not final_text:

        return HttpResponse(

            'Please provide the final application text.',

            status=400,

        )



    if len(final_text) < 10:

        return HttpResponse(

            'Please provide at least 10 characters.',

            status=400,

        )



    ticket_type_code = (

        request.POST.get('ticket_type')

        or request.session.get('ticket_type')

        or 'complaint'

    ).strip()



    try:

        selected_type = (

            ConfigService.ticket_type_by_code(

                ticket_type_code

            )

        )



        if not selected_type:

            ticket_types = ConfigService.ticket_types()



            if ticket_types:

                selected_type = ticket_types[0]

                ticket_type_code = selected_type.code



            else:

                return HttpResponse(

                    'No ticket types are configured.',

                    status=400,

                )



        dynamic_data = {}



        from apps.core.form_schema import extract_dynamic_data



        schema = (

            selected_type.dynamic_schema

            or {}

        )



        if schema:

            dynamic_data, errors = extract_dynamic_data(

                schema,

                request.POST,

                request.FILES,

            )



            if errors:

                return HttpResponse(

                    '<br>'.join(errors),

                    status=400,

                )



        ticket = create_ticket(

            student=request.user,

            ticket_type=ticket_type_code,

            raw_input=final_text,

            subject=final_text[:100],

        )



        ticket.dynamic_data = dynamic_data



        if hasattr(

            ticket,

            'ai_metadata',

        ):

            ticket.ai_metadata = (

                ticket.ai_metadata

                or {}

            )



            ticket.ai_metadata[

                'submission_source'

            ] = 'ai_preview_confirm'



            ticket.ai_metadata[

                'final_text_confirmed_by_student'

            ] = True



        update_fields = [

            'dynamic_data'

        ]



        if hasattr(

            ticket,

            'ai_metadata',

        ):

            update_fields.append(

                'ai_metadata'

            )



        ticket.save(

            update_fields=update_fields

        )



        from apps.workflows.engine import WorkflowEngine



        WorkflowEngine.attach_workflow(

            ticket

        )



        messages.success(

            request,

            f"Ticket #{ticket.id} submitted successfully.",

        )



        request.session.pop(

            'ticket_type',

            None,

        )



        return redirect(

            'tickets:detail',

            pk=ticket.id,

        )



    except Exception as exc:

        import logging



        logging.getLogger(

            __name__

        ).exception(

            "Failed to confirm ticket submission: %s",

            exc,

        )



        messages.error(

            request,

            "Unable to submit the application. Please try again.",

        )



        return redirect(

            'tickets:submit'

        )