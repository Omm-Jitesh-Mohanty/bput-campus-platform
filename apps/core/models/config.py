"""
Config-driven models — the heart of the platform's extensibility.

Everything here is editable by admins at runtime, without code changes.
This is what makes the platform "real-world" instead of a hackathon toy.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from .base import TimeStampedModel


# =====================================================================
# Department
# =====================================================================
class Department(TimeStampedModel):
    """
    A configurable department/unit. Replaces hard-coded DEPARTMENTS list.
    
    Supports hierarchical organization (e.g., Electrical is child of Maintenance).
    Includes routing keywords for AI-based auto-assignment.
    """
    code = models.SlugField(
        max_length=30, unique=True,
        help_text="Short code used in URLs and APIs (e.g., 'cse', 'plumbing')"
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    icon = models.CharField(
        max_length=10, default='🏢',
        help_text="Emoji icon shown in UI"
    )
    color = models.CharField(
        max_length=7, default='#1e40af',
        help_text="Hex color for badges/charts"
    )

    # Hierarchy
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='children',
        help_text="Parent department (leave blank for top-level)"
    )

    # Contact
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='headed_departments',
        help_text="Department head / HOD"
    )
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    office_location = models.CharField(max_length=200, blank=True)

    # SLA & routing
    default_sla_hours = models.PositiveIntegerField(
        default=48,
        validators=[MinValueValidator(1), MaxValueValidator(720)],
        help_text="Default SLA in hours for tickets assigned to this department"
    )
    routing_keywords = models.JSONField(
        default=list, blank=True,
        help_text=(
            "List of lowercase keywords used by AI router. "
            "Example: ['tap', 'leak', 'water', 'pipe']"
        )
    )
    auto_route_enabled = models.BooleanField(
        default=True,
        help_text="If enabled, AI auto-routes matching tickets here"
    )

    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['is_active', 'sort_order']),
        ]

    def __str__(self):
        return f"{self.icon} {self.name}"

    def get_full_path(self):
        """Return human-readable hierarchy path."""
        if self.parent:
            return f"{self.parent.get_full_path()} → {self.name}"
        return self.name

    def get_descendants(self, include_self=True):
        """Return list of self + all child departments (recursive)."""
        result = [self] if include_self else []
        for child in self.children.all():
            result.extend(child.get_descendants(include_self=True))
        return result

    def all_keywords(self):
        """Aggregate keywords from self + descendants."""
        keywords = set(self.routing_keywords or [])
        for child in self.children.all():
            keywords.update(child.all_keywords())
        return list(keywords)


class DepartmentMembership(TimeStampedModel):
    """
    Links a user (admin/staff) to a department with a specific role.
    A user can belong to multiple departments.
    """
    ROLE_IN_DEPT = [
        ('staff', 'Staff'),
        ('head', 'Department Head'),
        ('assistant', 'Assistant'),
        ('observer', 'Observer'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='department_memberships'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role_in_dept = models.CharField(
        max_length=20, choices=ROLE_IN_DEPT, default='staff'
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Is this the user's primary department?"
    )
    joined_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('user', 'department')
        ordering = ['-is_primary', 'department__name']

    def __str__(self):
        return f"{self.user.username} @ {self.department.code} ({self.role_in_dept})"


# =====================================================================
# Priority Level
# =====================================================================
class PriorityLevel(TimeStampedModel):
    """
    Configurable priority tiers. Replaces hard-coded PRIORITY_CHOICES.
    """
    code = models.SlugField(
        max_length=20, unique=True,
        help_text="Machine name (e.g., 'low', 'urgent')"
    )
    name = models.CharField(max_length=50)
    color = models.CharField(
        max_length=7, default='#64748b',
        help_text="Hex color for badge"
    )
    weight = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Higher weight = more urgent (used in ranking)"
    )
    sla_multiplier = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.00,
        help_text="Multiplier applied to base SLA (e.g., 0.5 = half time for urgent)"
    )
    icon = models.CharField(max_length=10, default='🟡')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ['-weight', 'sort_order']

    def __str__(self):
        return f"{self.icon} {self.name}"


# =====================================================================
# Ticket Type
# =====================================================================
class TicketType(TimeStampedModel):
    """
    Configurable ticket type. Replaces hard-coded TICKET_TYPE_CHOICES.

    Each type carries a 'dynamic_schema' — a JSON Schema describing
    what extra fields are needed for this type of request.

    Example schema for 'Bonafide Certificate':
        {
            "fields": [
                {"name": "purpose", "label": "Purpose", "type": "select",
                 "options": ["Bank Loan", "Passport", "Higher Studies", "Other"],
                 "required": True},
                {"name": "addressed_to", "label": "Addressed To",
                 "type": "text", "required": False}
            ]
        }
    """
    code = models.SlugField(
        max_length=30, unique=True,
        help_text="Machine name (e.g., 'complaint', 'leave', 'bonafide')"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default='📄')

    # Default routing
    default_department = models.ForeignKey(
        Department,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='default_ticket_types',
        help_text="Fallback department if AI can't route"
    )

    # SLA
    sla_hours = models.PositiveIntegerField(
        default=48,
        help_text="Base SLA in hours (multiplied by priority's sla_multiplier)"
    )

    # Attachments
    requires_attachment = models.BooleanField(default=False)
    allowed_attachment_types = models.JSONField(
        default=list, blank=True,
        help_text="e.g. ['pdf', 'jpg', 'png']. Empty = all allowed."
    )
    max_attachment_mb = models.PositiveIntegerField(default=5)

    # Dynamic form
    dynamic_schema = models.JSONField(
        default=dict, blank=True,
        help_text="JSON Schema defining extra form fields for this type"
    )
    ai_hints = models.JSONField(
        default=dict, blank=True,
        help_text=(
            "Hints for AI formatter. "
            "e.g. {'tone': 'formal', 'required_sections': ['purpose', 'duration']}"
        )
    )

    # Workflow (set in Step 10)
    # workflow = models.ForeignKey('Workflow', null=True, on_delete=models.SET_NULL)

    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.icon} {self.name}"


# =====================================================================
# SLA Policy
# =====================================================================
class SLAPolicy(TimeStampedModel):
    """
    Per-(ticket_type, priority) SLA thresholds.
    Overrides the ticket type's base sla_hours if present.

    Green: below this → on time
    Yellow: between green and yellow → watch
    Red: between yellow and red → critical
    Escalation: after red hours → auto-escalate
    """
    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.CASCADE,
        related_name='sla_policies'
    )
    priority = models.ForeignKey(
        PriorityLevel,
        on_delete=models.CASCADE,
        related_name='sla_policies'
    )

    green_hours = models.PositiveIntegerField(default=24)
    yellow_hours = models.PositiveIntegerField(default=48)
    red_hours = models.PositiveIntegerField(default=72)

    # Escalation
    auto_escalate = models.BooleanField(
        default=True,
        help_text="Auto-escalate if not resolved by red_hours"
    )
    escalation_target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='escalation_target_for',
        help_text="Who gets notified on escalation"
    )
    escalation_after_hours = models.PositiveIntegerField(
        default=72,
        help_text="Escalate if not resolved after this many hours"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('ticket_type', 'priority')
        ordering = ['ticket_type', '-priority__weight']

    def __str__(self):
        return f"{self.ticket_type.code} / {self.priority.code} → {self.green_hours}h/{self.yellow_hours}h/{self.red_hours}h"

    def clean(self):
        """Ensure thresholds are in ascending order."""
        from django.core.exceptions import ValidationError
        if not (self.green_hours <= self.yellow_hours <= self.red_hours):
            raise ValidationError(
                "SLA hours must be in ascending order: green ≤ yellow ≤ red"
            )


# =====================================================================
# System Setting
# =====================================================================
class SystemSetting(TimeStampedModel):
    """
    Global key-value store for runtime configuration.

    Examples:
        key='attendance.threshold_pct'  value=75
        key='ticket.auto_close_days'    value=7
        key='ui.default_language'       value='en'
        key='ai.confidence_threshold'   value=0.7
    """
    VALUE_TYPES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.JSONField()
    value_type = models.CharField(max_length=20, choices=VALUE_TYPES, default='string')
    category = models.CharField(
        max_length=50, default='general', db_index=True,
        help_text="Grouping for admin UI (e.g., 'attendance', 'ai', 'ui')"
    )
    label = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(
        default=False,
        help_text="If True, value is exposed to frontend (safe for non-secrets)"
    )
    editable_by_role = models.CharField(
        max_length=20, default='principal',
        help_text="Minimum role required to edit (student/teacher/warden/hod/dean/principal)"
    )

    class Meta:
        ordering = ['category', 'key']

    def __str__(self):
        return f"{self.key} = {self.value!r}"


# =====================================================================
# Audit Log
# =====================================================================
class AuditLog(models.Model):
    """
    Immutable record of every significant action in the system.

    Never edited, never deleted. Enables compliance, forensics, and
    "who changed what when" queries.
    """
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('escalate', 'Escalate'),
        ('assign', 'Assign'),
        ('resolve', 'Resolve'),
        ('config_change', 'Config Change'),
        ('permission_change', 'Permission Change'),
        ('data_export', 'Data Export'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=30, choices=ACTION_TYPES, db_index=True)

    # What was affected
    target_model = models.CharField(max_length=100, blank=True, db_index=True)
    target_id = models.CharField(max_length=50, blank=True)
    target_repr = models.CharField(max_length=200, blank=True)

    # Context
    changes = models.JSONField(
        default=dict, blank=True,
        help_text="{field_name: {'old': ..., 'new': ...}}"
    )
    metadata = models.JSONField(default=dict, blank=True)

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'action']),
            models.Index(fields=['target_model', 'target_id']),
            models.Index(fields=['user', '-timestamp']),
        ]

    def __str__(self):
        who = self.user.username if self.user else 'system'
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {who} {self.action} {self.target_model}#{self.target_id}"


# =====================================================================
# Notification Template
# =====================================================================
class NotificationTemplate(TimeStampedModel):
    """
    Editable templates for emails/SMS/in-app messages.

    Uses Django template syntax. Available context variables
    are documented per event_code.
    """
    CHANNELS = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('in_app', 'In-App'),
        ('push', 'Browser Push'),
    ]
    LANGUAGES = [
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('or', 'Odia'),
    ]

    event_code = models.SlugField(
        max_length=60, db_index=True,
        help_text="Event trigger (e.g., 'ticket.created', 'ticket.resolved')"
    )
    channel = models.CharField(max_length=20, choices=CHANNELS, db_index=True)
    language = models.CharField(max_length=5, choices=LANGUAGES, default='en')

    subject_template = models.CharField(
        max_length=200, blank=True,
        help_text="Subject line (Email only)"
    )
    body_template = models.TextField(
        help_text="Template body. Uses Django template syntax: {{ student_name }}"
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('event_code', 'channel', 'language')
        ordering = ['event_code', 'channel', 'language']

    def __str__(self):
        return f"{self.event_code} / {self.channel} / {self.language}"

    def render(self, context):
        """Render subject + body with given context."""
        from django.template import Template, Context
        ctx = Context(context)
        subject = Template(self.subject_template).render(ctx) if self.subject_template else ''
        body = Template(self.body_template).render(ctx)
        return subject, body


# =====================================================================
# AI Prompt Template (versioned)
# =====================================================================
class AIPromptTemplate(TimeStampedModel):
    """
    Versioned prompt templates. Enables A/B testing and rollback.

    Only ONE template per (key, is_active=True) should exist at a time.
    """
    key = models.SlugField(
        max_length=80, db_index=True,
        help_text="Prompt identifier (e.g., 'ticket.formatter')"
    )
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(
        default=False,
        help_text="Only one active version per key"
    )

    system_prompt = models.TextField(
        blank=True,
        help_text="System-level instructions"
    )
    user_prompt_template = models.TextField(
        help_text="User prompt. Django syntax: {{ raw_input }}"
    )

    # Metadata for A/B testing
    model_name = models.CharField(
        max_length=100, blank=True,
        help_text="Override default model (e.g., 'llama3.2:3b')"
    )
    temperature = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.30
    )
    max_tokens = models.PositiveIntegerField(default=500)

    # Performance tracking
    times_used = models.PositiveIntegerField(default=0)
    avg_latency_ms = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='created_prompts'
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('key', 'version')
        ordering = ['key', '-version']
        indexes = [
            models.Index(fields=['key', 'is_active']),
        ]

    def __str__(self):
        active = '✓' if self.is_active else ' '
        return f"[{active}] {self.key} v{self.version}"

    def save(self, *args, **kwargs):
        """
        If this instance is being marked active, deactivate all
        other versions of the same key.
        """
        if self.is_active:
            AIPromptTemplate.objects.filter(
                key=self.key, is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)