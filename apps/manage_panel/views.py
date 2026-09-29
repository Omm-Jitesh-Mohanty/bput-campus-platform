from django.shortcuts import render

# Create your views here.
"""
Custom admin management portal.
"""
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction


def config_admin_required(view_func):
    """
    Only allow principals, deans, HODs, and wardens into the manage panel.
    Students and teachers cannot access.
    """
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        allowed_roles = ['principal', 'dean', 'hod', 'warden']
        if request.user.role not in allowed_roles:
            raise PermissionDenied("You don't have permission to access the management panel.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def _ctx(request, section):
    """Build base context for manage panel pages."""
    return {'manage_section': section}

from apps.core.models import (
    Department, TicketType, PriorityLevel, SLAPolicy,
    SystemSetting, AIPromptTemplate, NotificationTemplate, AuditLog,
)
from apps.core.services import ConfigService


@config_admin_required
def manage_home(request):
    """Overview: config counts, recent changes, quick links."""
    ctx = _ctx(request, 'home')
    ctx.update({
        'counts': {
            'departments': Department.objects.count(),
            'active_departments': Department.objects.filter(is_active=True).count(),
            'ticket_types': TicketType.objects.count(),
            'priorities': PriorityLevel.objects.count(),
            'sla_policies': SLAPolicy.objects.count(),
            'settings': SystemSetting.objects.count(),
            'prompts': AIPromptTemplate.objects.filter(is_active=True).count(),
            'notification_templates': NotificationTemplate.objects.count(),
        },
        'recent_audit': AuditLog.objects.select_related('user').order_by('-timestamp')[:8],
        'recent_config_changes': (
            AuditLog.objects
            .filter(action='config_change')
            .select_related('user')
            .order_by('-timestamp')[:5]
        ),
    })
    return render(request, 'manage_panel/home.html', ctx)

@config_admin_required
def departments_list(request):
    ctx = _ctx(request, 'departments')
    ctx['departments'] = Department.objects.all().order_by('sort_order', 'name')
    return render(request, 'manage_panel/departments/list.html', ctx)


@config_admin_required
def department_edit(request, pk=None):
    """Create or edit a department."""
    ctx = _ctx(request, 'departments')
    instance = get_object_or_404(Department, pk=pk) if pk else None

    if request.method == 'POST':
        data = request.POST

        with transaction.atomic():
            if instance is None:
                instance = Department()
                created = True
            else:
                created = False

            instance.code = data.get('code', '').strip().lower().replace(' ', '_')
            instance.name = data.get('name', '').strip()
            instance.description = data.get('description', '').strip()
            instance.icon = data.get('icon', '🏢').strip() or '🏢'
            instance.color = data.get('color', '#1e40af').strip()
            instance.contact_email = data.get('contact_email', '').strip()
            instance.contact_phone = data.get('contact_phone', '').strip()
            instance.office_location = data.get('office_location', '').strip()
            instance.default_sla_hours = int(data.get('default_sla_hours', 48))
            instance.auto_route_enabled = data.get('auto_route_enabled') == 'on'
            instance.is_active = data.get('is_active') == 'on'
            instance.sort_order = int(data.get('sort_order', 100))

            # Parent
            parent_id = data.get('parent')
            instance.parent = Department.objects.filter(pk=parent_id).first() if parent_id else None

            # Head
            head_id = data.get('head')
            if head_id:
                from apps.accounts.models import User
                instance.head = User.objects.filter(pk=head_id).first()
            else:
                instance.head = None

            # Keywords — sent as JSON string from chip editor
            import json
            keywords_raw = data.get('routing_keywords', '[]')
            try:
                keywords = json.loads(keywords_raw)
                if not isinstance(keywords, list):
                    keywords = []
                instance.routing_keywords = [str(k).strip().lower() for k in keywords if k]
            except json.JSONDecodeError:
                instance.routing_keywords = []

            instance.save()

        messages.success(
            request,
            f"Department '{instance.name}' {'created' if created else 'updated'}."
        )
        return redirect('manage_panel:department_edit', pk=instance.pk)

    ctx['dept'] = instance
    ctx['all_departments'] = Department.objects.exclude(pk=instance.pk if instance else None)
    ctx['all_admins'] = (
        __import__('apps.accounts.models', fromlist=['User']).User.objects
        .filter(role__in=['teacher', 'warden', 'hod', 'dean', 'principal'])
        .order_by('first_name')
    )
    ctx['keywords_json'] = __import__('json').dumps(
        instance.routing_keywords if instance else []
    )
    return render(request, 'manage_panel/departments/edit.html', ctx)


@config_admin_required
@require_POST
def department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if dept.children.exists():
        messages.error(request, "Cannot delete — has child departments.")
    else:
        name = dept.name
        dept.delete()
        messages.success(request, f"Department '{name}' deleted.")
    return redirect('manage_panel:departments')

@config_admin_required
def slas_view(request):
    """Visual SLA matrix: rows = ticket types, cols = priorities."""
    ctx = _ctx(request, 'slas')

    ticket_types = ConfigService.ticket_types(active_only=False)
    priorities = ConfigService.priority_levels(active_only=False)

    # Build lookup: (tt_code, prio_code) -> SLAPolicy
    existing = {
        (p.ticket_type.code, p.priority.code): p
        for p in SLAPolicy.objects.all().select_related('ticket_type', 'priority')
    }

    # Build matrix
    matrix = []
    for tt in ticket_types:
        row = {
            'ticket_type': tt,
            'cells': []
        }
        for p in priorities:
            policy = existing.get((tt.code, p.code))
            row['cells'].append({
                'priority': p,
                'policy': policy,
                'green': policy.green_hours if policy else '—',
                'yellow': policy.yellow_hours if policy else '—',
                'red': policy.red_hours if policy else '—',
            })
        matrix.append(row)

    ctx['matrix'] = matrix
    ctx['priorities'] = priorities
    return render(request, 'manage_panel/slas/matrix.html', ctx)


@config_admin_required
@require_POST
def sla_update_ajax(request):
    """AJAX endpoint to update a single SLA cell."""
    import json
    from django.http import JsonResponse

    data = json.loads(request.body)
    tt_code = data.get('ticket_type')
    prio_code = data.get('priority')
    green = int(data.get('green', 24))
    yellow = int(data.get('yellow', 48))
    red = int(data.get('red', 72))

    if not (green <= yellow <= red):
        return JsonResponse({'ok': False, 'error': 'green ≤ yellow ≤ red'}, status=400)

    tt = TicketType.objects.filter(code=tt_code).first()
    prio = PriorityLevel.objects.filter(code=prio_code).first()

    if not tt or not prio:
        return JsonResponse({'ok': False, 'error': 'Not found'}, status=404)

    policy, created = SLAPolicy.objects.get_or_create(
        ticket_type=tt,
        priority=prio,
        defaults={'green_hours': green, 'yellow_hours': yellow, 'red_hours': red},
    )
    if not created:
        policy.green_hours = green
        policy.yellow_hours = yellow
        policy.red_hours = red
        policy.save()

    return JsonResponse({'ok': True, 'created': created})

# =====================================================================
# Ticket Types
# =====================================================================

@config_admin_required
def ticket_types_list(request):
    """List all configurable ticket types."""
    ctx = _ctx(request, 'ticket_types')

    ctx['ticket_types'] = (
        TicketType.objects
        .select_related('default_department')
        .all()
        .order_by('sort_order', 'name')
    )

    return render(request, 'manage_panel/ticket_types/list.html', ctx)


@config_admin_required
def ticket_type_edit(request, pk=None):
    """Create or edit a ticket type."""
    ctx = _ctx(request, 'ticket_types')

    instance = (
        get_object_or_404(TicketType, pk=pk)
        if pk
        else None
    )

    if request.method == 'POST':
        data = request.POST

        import json

        with transaction.atomic():
            if instance is None:
                instance = TicketType()
                created = True
            else:
                created = False

            instance.code = (
                data.get('code', '')
                .strip()
                .lower()
                .replace(' ', '_')
            )

            instance.name = data.get('name', '').strip()
            instance.description = data.get('description', '').strip()
            instance.icon = data.get('icon', '📄').strip() or '📄'

            department_id = data.get('default_department')
            instance.default_department = (
                Department.objects.filter(pk=department_id).first()
                if department_id
                else None
            )

            instance.sla_hours = int(
                data.get('sla_hours', 48)
            )

            instance.requires_attachment = (
                data.get('requires_attachment') == 'on'
            )

            allowed_types_raw = data.get(
                'allowed_attachment_types',
                '[]'
            )

            try:
                allowed_types = json.loads(allowed_types_raw)

                if not isinstance(allowed_types, list):
                    allowed_types = []

                instance.allowed_attachment_types = [
                    str(item).strip().lower()
                    for item in allowed_types
                    if str(item).strip()
                ]

            except json.JSONDecodeError:
                instance.allowed_attachment_types = []

            instance.max_attachment_mb = int(
                data.get('max_attachment_mb', 5)
            )

            dynamic_schema_raw = data.get(
                'dynamic_schema',
                '{}'
            )

            try:
                dynamic_schema = json.loads(
                    dynamic_schema_raw
                )

                if not isinstance(dynamic_schema, dict):
                    dynamic_schema = {}

                instance.dynamic_schema = dynamic_schema

            except json.JSONDecodeError:
                instance.dynamic_schema = {}

            ai_hints_raw = data.get(
                'ai_hints',
                '{}'
            )

            try:
                ai_hints = json.loads(ai_hints_raw)

                if not isinstance(ai_hints, dict):
                    ai_hints = {}

                instance.ai_hints = ai_hints

            except json.JSONDecodeError:
                instance.ai_hints = {}

            instance.is_active = (
                data.get('is_active') == 'on'
            )

            instance.sort_order = int(
                data.get('sort_order', 100)
            )

            instance.save()

        messages.success(
            request,
            f"Ticket type '{instance.name}' "
            f"{'created' if created else 'updated'}."
        )

        return redirect(
            'manage_panel:ticket_type_edit',
            pk=instance.pk
        )

    ctx['ticket_type'] = instance

    ctx['departments'] = (
        Department.objects
        .filter(is_active=True)
        .order_by('sort_order', 'name')
    )

    ctx['allowed_types_json'] = __import__('json').dumps(
        instance.allowed_attachment_types
        if instance
        else []
    )

    ctx['dynamic_schema_json'] = __import__('json').dumps(
        instance.dynamic_schema
        if instance
        else {}
    )

    ctx['ai_hints_json'] = __import__('json').dumps(
        instance.ai_hints
        if instance
        else {}
    )

    return render(
        request,
        'manage_panel/ticket_types/edit.html',
        ctx
    )


@config_admin_required
@require_POST
def ticket_type_delete(request, pk):
    """Delete a ticket type."""
    ticket_type = get_object_or_404(
        TicketType,
        pk=pk
    )

    name = ticket_type.name

    ticket_type.delete()

    messages.success(
        request,
        f"Ticket type '{name}' deleted."
    )

    return redirect(
        'manage_panel:ticket_types'
    )

# =====================================================================
# Priorities
# =====================================================================

@config_admin_required
def priorities_list(request):
    """List all configurable priority levels."""
    ctx = _ctx(request, 'priorities')

    ctx['priorities'] = (
        PriorityLevel.objects
        .all()
        .order_by('-weight', 'sort_order', 'name')
    )

    return render(
        request,
        'manage_panel/priorities/list.html',
        ctx
    )


@config_admin_required
def priority_edit(request, pk=None):
    """Create or edit a priority level."""
    ctx = _ctx(request, 'priorities')

    instance = (
        get_object_or_404(PriorityLevel, pk=pk)
        if pk
        else None
    )

    if request.method == 'POST':
        data = request.POST

        with transaction.atomic():
            if instance is None:
                instance = PriorityLevel()
                created = True
            else:
                created = False

            instance.code = (
                data.get('code', '')
                .strip()
                .lower()
                .replace(' ', '_')
            )

            instance.name = data.get('name', '').strip()

            instance.color = (
                data.get('color', '#64748b').strip()
                or '#64748b'
            )

            instance.weight = int(
                data.get('weight', 50)
            )

            instance.sla_multiplier = data.get(
                'sla_multiplier',
                '1.00'
            )

            instance.icon = (
                data.get('icon', '🟡').strip()
                or '🟡'
            )

            instance.is_active = (
                data.get('is_active') == 'on'
            )

            instance.sort_order = int(
                data.get('sort_order', 100)
            )

            instance.save()

        messages.success(
            request,
            f"Priority '{instance.name}' "
            f"{'created' if created else 'updated'}."
        )

        return redirect(
            'manage_panel:priority_edit',
            pk=instance.pk
        )

    ctx['priority'] = instance

    return render(
        request,
        'manage_panel/priorities/edit.html',
        ctx
    )


@config_admin_required
@require_POST
def priority_delete(request, pk):
    """Delete a priority level."""
    priority = get_object_or_404(
        PriorityLevel,
        pk=pk
    )

    name = priority.name

    priority.delete()

    messages.success(
        request,
        f"Priority '{name}' deleted."
    )

    return redirect(
        'manage_panel:priorities'
    )

# =====================================================================
# System Settings
# =====================================================================

@config_admin_required
def settings_list(request):
    """List all system settings."""
    ctx = _ctx(request, 'settings')

    ctx['settings'] = (
        SystemSetting.objects
        .all()
        .order_by('category', 'key')
    )

    return render(
        request,
        'manage_panel/settings/list.html',
        ctx
    )


@config_admin_required
def setting_edit(request, pk=None):
    """Create or edit a system setting."""
    ctx = _ctx(request, 'settings')

    instance = (
        get_object_or_404(SystemSetting, pk=pk)
        if pk
        else None
    )

    if request.method == 'POST':
        data = request.POST

        with transaction.atomic():
            if instance is None:
                instance = SystemSetting()
                created = True
            else:
                created = False

            instance.key = data.get('key', '').strip()
            instance.label = data.get('label', '').strip()
            instance.description = data.get('description', '').strip()
            instance.category = data.get(
                'category',
                'general'
            ).strip()

            instance.value_type = data.get(
                'value_type',
                'string'
            ).strip()

            raw_value = data.get('value', '').strip()

            if instance.value_type == 'integer':
                try:
                    instance.value = int(raw_value)
                except ValueError:
                    instance.value = 0

            elif instance.value_type == 'float':
                try:
                    instance.value = float(raw_value)
                except ValueError:
                    instance.value = 0.0

            elif instance.value_type == 'boolean':
                instance.value = raw_value.lower() in [
                    'true',
                    '1',
                    'yes',
                    'on'
                ]

            elif instance.value_type == 'json':
                import json

                try:
                    parsed_value = json.loads(raw_value)
                    instance.value = parsed_value
                except json.JSONDecodeError:
                    instance.value = {}

            else:
                instance.value = raw_value

            instance.is_public = (
                data.get('is_public') == 'on'
            )

            instance.editable_by_role = data.get(
                'editable_by_role',
                ''
            ).strip()

            instance.save()

        messages.success(
            request,
            f"Setting '{instance.key}' "
            f"{'created' if created else 'updated'}."
        )

        return redirect(
            'manage_panel:setting_edit',
            pk=instance.pk
        )

    ctx['setting'] = instance

    return render(
        request,
        'manage_panel/settings/edit.html',
        ctx
    )


@config_admin_required
@require_POST
def setting_delete(request, pk):
    """Delete a system setting."""
    setting = get_object_or_404(
        SystemSetting,
        pk=pk
    )

    key = setting.key

    setting.delete()

    messages.success(
        request,
        f"Setting '{key}' deleted."
    )

    return redirect(
        'manage_panel:settings'
    )


# =====================================================================
# AI Prompt Templates
# =====================================================================

@config_admin_required
def prompts_list(request):
    """List all AI prompt templates."""
    ctx = _ctx(request, 'prompts')

    ctx['prompts'] = (
        AIPromptTemplate.objects
        .select_related('created_by')
        .all()
        .order_by('key', '-version')
    )

    return render(
        request,
        'manage_panel/prompts/list.html',
        ctx
    )


@config_admin_required
def prompt_edit(request, pk=None):
    """Create or edit an AI prompt template."""
    ctx = _ctx(request, 'prompts')

    instance = (
        get_object_or_404(AIPromptTemplate, pk=pk)
        if pk
        else None
    )

    if request.method == 'POST':
        data = request.POST

        with transaction.atomic():
            if instance is None:
                instance = AIPromptTemplate()
                created = True
            else:
                created = False

            instance.key = data.get('key', '').strip()

            instance.version = int(
                data.get('version', 1)
            )

            instance.system_prompt = data.get(
                'system_prompt',
                ''
            ).strip()

            instance.user_prompt_template = data.get(
                'user_prompt_template',
                ''
            ).strip()

            instance.model_name = data.get(
                'model_name',
                ''
            ).strip()

            try:
                instance.temperature = float(
                    data.get('temperature', '0.7')
                )
            except (TypeError, ValueError):
                instance.temperature = 0.7

            try:
                instance.max_tokens = int(
                    data.get('max_tokens', '1024')
                )
            except (TypeError, ValueError):
                instance.max_tokens = 1024

            instance.notes = data.get(
                'notes',
                ''
            ).strip()

            instance.is_active = (
                data.get('is_active') == 'on'
            )

            if not instance.pk:
                instance.created_by = request.user

            instance.save()

        messages.success(
            request,
            f"AI prompt '{instance.key}' "
            f"{'created' if created else 'updated'}."
        )

        return redirect(
            'manage_panel:prompt_edit',
            pk=instance.pk
        )

    ctx['prompt'] = instance

    return render(
        request,
        'manage_panel/prompts/edit.html',
        ctx
    )


@config_admin_required
@require_POST
def prompt_delete(request, pk):
    """Delete an AI prompt template."""
    prompt = get_object_or_404(
        AIPromptTemplate,
        pk=pk
    )

    key = prompt.key

    prompt.delete()

    messages.success(
        request,
        f"AI prompt '{key}' deleted."
    )

    return redirect(
        'manage_panel:prompts'
    )


# =====================================================================
# Notification Templates
# =====================================================================

@config_admin_required
def notifications_list(request):
    """List all notification templates."""
    ctx = _ctx(request, 'notifications')

    ctx['notifications'] = (
        NotificationTemplate.objects
        .all()
        .order_by('event_code', 'channel', 'language')
    )

    return render(
        request,
        'manage_panel/notifications/list.html',
        ctx
    )


@config_admin_required
def notification_edit(request, pk=None):
    """Create or edit a notification template."""
    ctx = _ctx(request, 'notifications')

    instance = (
        get_object_or_404(NotificationTemplate, pk=pk)
        if pk
        else None
    )

    if request.method == 'POST':
        data = request.POST

        with transaction.atomic():
            if instance is None:
                instance = NotificationTemplate()
                created = True
            else:
                created = False

            instance.event_code = data.get(
                'event_code',
                ''
            ).strip()

            instance.channel = data.get(
                'channel',
                ''
            ).strip()

            instance.language = data.get(
                'language',
                'en'
            ).strip()

            instance.subject = data.get(
                'subject',
                ''
            ).strip()

            instance.body = data.get(
                'body',
                ''
            ).strip()

            instance.is_active = (
                data.get('is_active') == 'on'
            )

            instance.notes = data.get(
                'notes',
                ''
            ).strip()

            instance.save()

        messages.success(
            request,
            f"Notification template for "
            f"'{instance.event_code}' "
            f"{'created' if created else 'updated'}."
        )

        return redirect(
            'manage_panel:notification_edit',
            pk=instance.pk
        )

    ctx['notification'] = instance

    return render(
        request,
        'manage_panel/notifications/edit.html',
        ctx
    )


@config_admin_required
@require_POST
def notification_delete(request, pk):
    """Delete a notification template."""
    notification = get_object_or_404(
        NotificationTemplate,
        pk=pk
    )

    event_code = notification.event_code

    notification.delete()

    messages.success(
        request,
        f"Notification template '{event_code}' deleted."
    )

    return redirect(
        'manage_panel:notifications'
    )


# =====================================================================
# Audit Trail
# =====================================================================

@config_admin_required
def audit_view(request):
    """Display the system audit trail."""
    ctx = _ctx(request, 'audit')

    ctx['audit_logs'] = (
        AuditLog.objects
        .select_related('user')
        .all()
        .order_by('-timestamp')
    )

    return render(
        request,
        'manage_panel/audit/list.html',
        ctx
    )


@config_admin_required
def ticket_types_list(request):
    ctx = _ctx(request, 'ticket_types')
    ctx['ticket_types'] = TicketType.objects.all().order_by('sort_order', 'name')
    return render(request, 'manage_panel/ticket_types/list.html', ctx)


@config_admin_required
def ticket_type_edit(request, pk=None):
    """Create or edit a ticket type + its form schema."""
    import json
    ctx = _ctx(request, 'ticket_types')
    instance = get_object_or_404(TicketType, pk=pk) if pk else None

    if request.method == 'POST':
        data = request.POST

        with transaction.atomic():
            created = instance is None
            if created:
                instance = TicketType()

            instance.code = data.get('code', '').strip().lower().replace(' ', '_')
            instance.name = data.get('name', '').strip()
            instance.description = data.get('description', '').strip()
            instance.icon = data.get('icon', '📄').strip() or '📄'
            instance.sla_hours = int(data.get('sla_hours', 48))
            instance.requires_attachment = data.get('requires_attachment') == 'on'
            instance.is_active = data.get('is_active') == 'on'
            instance.sort_order = int(data.get('sort_order', 100))

            # Default department
            dept_id = data.get('default_department')
            instance.default_department = (
                Department.objects.filter(pk=dept_id).first() if dept_id else None
            )

            # Dynamic schema from form builder
            schema_json = data.get('dynamic_schema', '{"fields": []}')
            try:
                schema = json.loads(schema_json)
            except json.JSONDecodeError:
                schema = {'fields': []}
            instance.dynamic_schema = schema

            instance.save()

        messages.success(
            request,
            f"Ticket type '{instance.name}' {'created' if created else 'updated'}."
        )
        return redirect('manage_panel:ticket_type_edit', pk=instance.pk)

    ctx['tt'] = instance
    ctx['all_departments'] = Department.objects.filter(is_active=True)
    ctx['field_types'] = __import__('apps.core.form_schema', fromlist=['FIELD_TYPES']).FIELD_TYPES
    ctx['schema_json'] = json.dumps(
        instance.dynamic_schema if instance else {'fields': []},
        indent=2
    )
    return render(request, 'manage_panel/ticket_types/edit.html', ctx)


@config_admin_required
@require_POST
def ticket_type_validate_schema(request):
    """Validate schema on the fly (AJAX)."""
    import json
    from apps.core.form_schema import validate_schema

    try:
        payload = json.loads(request.body)
        schema = payload.get('schema', {})
        is_valid, errors = validate_schema(schema)
        return JsonResponse({'valid': is_valid, 'errors': errors})
    except Exception as e:
        return JsonResponse({'valid': False, 'errors': [str(e)]}, status=400)


@config_admin_required
def document_templates_list(request):
    ctx = _ctx(request, 'documents')
    from apps.documents.models import DocumentTemplate
    ctx['templates'] = DocumentTemplate.objects.all().order_by('doc_type', '-version')
    return render(request, 'manage_panel/documents/list.html', ctx)


@config_admin_required
def document_template_edit(request, pk=None):
    import json
    ctx = _ctx(request, 'documents')
    from apps.documents.models import DocumentTemplate
    from apps.documents.context import DATA_SOURCES
    from apps.core.constants import DOCUMENT_TYPES

    instance = get_object_or_404(DocumentTemplate, pk=pk) if pk else None

    if request.method == 'POST':
        from django.core.files.base import ContentFile

        instance = instance or DocumentTemplate()
        instance.doc_type = request.POST.get('doc_type', '')
        instance.name = request.POST.get('name', '')
        instance.description = request.POST.get('description', '')
        instance.version = int(request.POST.get('version', 1))
        instance.requires_fee_clearance = request.POST.get('requires_fee_clearance') == 'on'
        instance.requires_attendance_75 = request.POST.get('requires_attendance_75') == 'on'
        instance.is_active = request.POST.get('is_active') == 'on'

        if request.FILES.get('template_file'):
            instance.template_file = request.FILES['template_file']
            instance.detected_placeholders = []   # force rescan

        # Field mapping
        try:
            mapping = json.loads(request.POST.get('field_mapping', '{}'))
            instance.field_mapping = mapping
        except json.JSONDecodeError:
            messages.error(request, "Field mapping must be valid JSON.")
            return render(request, 'manage_panel/documents/edit.html', _doc_edit_ctx(ctx, instance, DATA_SOURCES, DOCUMENT_TYPES))

        instance.save()
        messages.success(request, f"Template '{instance.name}' saved.")
        return redirect('manage_panel:document_template_edit', pk=instance.pk)

    return render(request, 'manage_panel/documents/edit.html',
                  _doc_edit_ctx(ctx, instance, DATA_SOURCES, DOCUMENT_TYPES))


def _doc_edit_ctx(ctx, instance, data_sources, doc_types):
    import json
    ctx['template'] = instance
    ctx['data_sources'] = data_sources
    ctx['doc_types'] = doc_types
    ctx['mapping_json'] = json.dumps(
        instance.field_mapping if instance else {}, indent=2
    )
    return ctx
