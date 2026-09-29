# from django.db import models

# Create your models here.
"""
Workflow engine models.

A Workflow is a chain of WorkflowSteps. When a ticket is created,
the workflow is attached and steps are executed sequentially.

Step execution is tracked in TicketStepExecution (runtime state).
"""
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class Workflow(TimeStampedModel):
    """
    A configurable multi-step approval workflow.
    Each TicketType can have one active workflow.
    """
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Attach to a ticket type (nullable — some workflows may be standalone)
    ticket_type = models.ForeignKey(
        'core.TicketType',
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='workflows',
        help_text="Ticket types using this workflow"
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Auto-apply to matching ticket types if no other workflow is set"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='created_workflows'
    )

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['ticket_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def step_count(self):
        return self.steps.count()

    def first_step(self):
        return self.steps.order_by('order').first()


class WorkflowStep(TimeStampedModel):
    """
    A single approval step in a workflow.

    Approvers are determined by role_required OR specific_user.
    If condition is present, this step is only applied when the condition
    evaluates true against the ticket's dynamic_data + base fields.
    """
    ACTION_TYPES = [
        ('review', 'Review'),
        ('approve', 'Approve'),
        ('sign', 'Sign'),
        ('notify', 'Notify Only'),
        ('verify', 'Verify'),
    ]

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='steps'
    )
    order = models.PositiveIntegerField(
        default=1,
        help_text="Execution order (1, 2, 3, ...)"
    )
    name = models.CharField(max_length=200)

    # Who can act on this step
    role_required = models.CharField(
        max_length=20, blank=True,
        choices=[
            ('teacher', 'Teacher'),
            ('warden', 'Warden'),
            ('hod', 'HOD'),
            ('dean', 'Dean'),
            ('principal', 'Principal'),
            ('', '—'),
        ],
        help_text="Role required to approve this step"
    )
    specific_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_workflow_steps',
        help_text="Specific person (overrides role if set)"
    )

    action_type = models.CharField(
        max_length=20, choices=ACTION_TYPES, default='approve'
    )

    # Conditional routing (JSON)
    condition = models.JSONField(
        default=dict, blank=True,
        help_text=(
            "Condition for this step to run. "
            "Example: {'field': 'dynamic_data.estimated_cost', 'operator': '>', 'value': 5000}"
        )
    )

    # Instructions shown to approver
    instructions = models.TextField(blank=True)

    # Auto-advance
    auto_advance_after_hours = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="If no action in N hours, auto-advance (or escalate). Null = manual."
    )
    auto_action = models.CharField(
        max_length=20, default='notify',
        choices=[('notify', 'Notify Escalation'), ('approve', 'Auto-approve'), ('reject', 'Auto-reject')]
    )

    # Skippable
    can_skip = models.BooleanField(
        default=False,
        help_text="Can approver skip this step?"
    )

    class Meta:
        ordering = ['workflow', 'order']
        unique_together = ('workflow', 'order')

    def __str__(self):
        return f"{self.workflow.code} → {self.order}. {self.name}"


class TicketStepExecution(TimeStampedModel):
    """
    Runtime state of a step for a specific ticket.
    Created when the ticket reaches this step.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Action'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
        ('escalated', 'Escalated'),
    ]

    ticket = models.ForeignKey(
        'tickets.CampusTicket',
        on_delete=models.CASCADE,
        related_name='step_executions'
    )
    workflow_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True
    )

    # Who acted (if any)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='step_actions'
    )
    acted_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)

    # For skipped steps
    skip_reason = models.CharField(max_length=200, blank=True)

    # For escalations
    escalated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='escalated_steps'
    )
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['ticket', 'workflow_step__order']
        unique_together = ('ticket', 'workflow_step')
        indexes = [
            models.Index(fields=['ticket', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Ticket #{self.ticket_id} — Step {self.workflow_step.order} ({self.status})"

    @property
    def is_terminal(self):
        return self.status in ('approved', 'rejected', 'skipped')