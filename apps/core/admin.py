# from django.contrib import admin

# Register your models here.
"""
Admin configuration for config-driven models.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Department, DepartmentMembership,
    PriorityLevel, TicketType, SLAPolicy,
    SystemSetting, AuditLog,
    NotificationTemplate, AIPromptTemplate,
)


# =====================================================================
# Department
# =====================================================================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('icon_badge', 'name', 'code', 'parent', 'head',
                    'default_sla_hours', 'keyword_count', 'is_active')
    list_filter = ('is_active', 'parent', 'auto_route_enabled')
    search_fields = ('code', 'name', 'description', 'routing_keywords')
    autocomplete_fields = ('head', 'parent')
    list_editable = ('is_active',)

    fieldsets = (
        ('Identity', {
            'fields': ('code', 'name', 'description', 'icon', 'color')
        }),
        ('Hierarchy', {
            'fields': ('parent', 'sort_order')
        }),
        ('Contact & Head', {
            'fields': ('head', 'contact_email', 'contact_phone', 'office_location')
        }),
        ('SLA & Routing', {
            'fields': ('default_sla_hours', 'routing_keywords', 'auto_route_enabled'),
            'description': (
                "Keywords are lowercase. AI will route tickets containing any "
                "of these words to this department (if auto-route is enabled)."
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def icon_badge(self, obj):
        return format_html(
            '<span style="font-size:18px">{}</span>', obj.icon
        )
    icon_badge.short_description = ''

    def keyword_count(self, obj):
        n = len(obj.routing_keywords or [])
        if n == 0:
            return '—'
        return format_html('<span title="{}">{} keywords</span>',
                           ', '.join(obj.routing_keywords[:5]), n)
    keyword_count.short_description = 'Keywords'


@admin.register(DepartmentMembership)
class DepartmentMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'role_in_dept',
                    'is_primary', 'joined_at')
    list_filter = ('department', 'role_in_dept', 'is_primary')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user', 'department')


# =====================================================================
# Priority Level
# =====================================================================
@admin.register(PriorityLevel)
class PriorityLevelAdmin(admin.ModelAdmin):
    list_display = ('icon_name', 'code', 'weight', 'sla_multiplier',
                    'sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
    list_editable = ('weight', 'sla_multiplier', 'sort_order', 'is_active')

    def icon_name(self, obj):
        return format_html('{} {}', obj.icon, obj.name)
    icon_name.short_description = 'Priority'


# =====================================================================
# Ticket Type
# =====================================================================
@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('icon_name', 'code', 'default_department',
                    'sla_hours', 'field_count', 'is_active', 'sort_order')
    list_filter = ('is_active', 'default_department', 'requires_attachment')
    search_fields = ('code', 'name', 'description')
    autocomplete_fields = ('default_department',)
    list_editable = ('sla_hours', 'is_active', 'sort_order')

    fieldsets = (
        ('Identity', {
            'fields': ('code', 'name', 'description', 'icon', 'sort_order')
        }),
        ('Routing', {
            'fields': ('default_department', 'sla_hours')
        }),
        ('Attachments', {
            'fields': ('requires_attachment', 'allowed_attachment_types',
                       'max_attachment_mb')
        }),
        ('Dynamic Form', {
            'fields': ('dynamic_schema', 'ai_hints'),
            'description': (
                'Define extra fields students fill. '
                'Format: {"fields": [{"name": "purpose", "type": "text", '
                '"label": "Purpose", "required": true}]}'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def icon_name(self, obj):
        return format_html('{} {}', obj.icon, obj.name)
    icon_name.short_description = 'Type'

    def field_count(self, obj):
        return len((obj.dynamic_schema or {}).get('fields', []))
    field_count.short_description = 'Fields'


# =====================================================================
# SLA Policy
# =====================================================================
@admin.register(SLAPolicy)
class SLAPolicyAdmin(admin.ModelAdmin):
    list_display = ('ticket_type', 'priority', 'green_hours',
                    'yellow_hours', 'red_hours', 'auto_escalate',
                    'escalation_target', 'is_active')
    list_filter = ('ticket_type', 'priority', 'auto_escalate', 'is_active')
    autocomplete_fields = ('ticket_type', 'priority', 'escalation_target')
    list_editable = ('green_hours', 'yellow_hours', 'red_hours', 'is_active')

    fieldsets = (
        ('Scope', {
            'fields': ('ticket_type', 'priority')
        }),
        ('Thresholds (hours)', {
            'fields': ('green_hours', 'yellow_hours', 'red_hours'),
            'description': 'green ≤ yellow ≤ red. Enforced on save.'
        }),
        ('Escalation', {
            'fields': ('auto_escalate', 'escalation_target', 'escalation_after_hours')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


# =====================================================================
# System Setting
# =====================================================================
@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'short_value', 'value_type', 'category',
                    'editable_by_role', 'is_public', 'updated_at')
    list_filter = ('category', 'value_type', 'is_public', 'editable_by_role')
    search_fields = ('key', 'description', 'label')
    list_editable = ('is_public',)

    def short_value(self, obj):
        v = repr(obj.value)
        return v[:60] + '…' if len(v) > 60 else v
    short_value.short_description = 'Value'


# =====================================================================
# Audit Log (read-only)
# =====================================================================
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'target_model',
                    'target_id', 'short_target')
    list_filter = ('action', 'target_model', 'timestamp')
    search_fields = ('user__username', 'target_model', 'target_id', 'target_repr')
    date_hierarchy = 'timestamp'
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def short_target(self, obj):
        return obj.target_repr[:60]
    short_target.short_description = 'Target'


# =====================================================================
# Notification Template
# =====================================================================
@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('event_code', 'channel', 'language',
                    'subject_template', 'is_active', 'updated_at')
    list_filter = ('channel', 'language', 'is_active')
    search_fields = ('event_code', 'subject_template', 'body_template')
    list_editable = ('is_active',)


# =====================================================================
# AI Prompt Template
# =====================================================================
@admin.register(AIPromptTemplate)
class AIPromptTemplateAdmin(admin.ModelAdmin):
    list_display = ('key', 'version', 'is_active', 'model_name',
                'temperature', 'times_used', 'avg_latency_ms', 'updated_at')
    list_filter = ('key', 'is_active', 'model_name')
    search_fields = ('key', 'notes')
    autocomplete_fields = ('created_by',)
    list_editable = ('is_active',)

    fieldsets = (
        ('Identity', {
            'fields': ('key', 'version', 'is_active', 'created_by')
        }),
        ('Prompts', {
            'fields': ('system_prompt', 'user_prompt_template'),
        }),
        ('Model Parameters', {
            'fields': ('model_name', 'temperature', 'max_tokens')
        }),
        ('Performance', {
            'fields': ('times_used', 'avg_latency_ms'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

    def active_badge(self, obj):
        if obj.is_active:
            return format_html('<b style="color:green">✓ Active</b>')
        return '—'
    active_badge.short_description = 'Status'


# =====================================================================
# Admin site branding
# =====================================================================
admin.site.site_header = 'BPUT Campus Platform — Administration'
admin.site.site_title = 'Campus Admin'
admin.site.index_title = 'Configuration & Operations'
