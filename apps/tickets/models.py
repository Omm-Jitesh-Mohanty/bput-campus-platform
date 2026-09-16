# from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.core.constants import (
    TICKET_TYPE_CHOICES, TICKET_STATUS_CHOICES, PRIORITY_CHOICES,
    TICKET_TYPE_LEAVE, TICKET_TYPE_GATEPASS, TICKET_TYPE_DOCUMENT, TICKET_TYPE_COMPLAINT,
    TICKET_STATUS_PENDING, TICKET_STATUS_RESOLVED, TICKET_STATUS_REOPENED,
    PRIORITY_MEDIUM, PRIORITY_HIGH,
    AGEING_GREEN_HOURS, AGEING_YELLOW_HOURS,
    ROUTING_DEPARTMENTS,
)
from apps.core.utils import ticket_attachment_path
from .validators import validate_upload_size, validate_upload_extension


class CampusTicket(TimeStampedModel, SoftDeleteModel):
    """
    Unified ticket model for:
      - Leave requests
      - Gate pass requests
      - Document / certificate requests
      - Complaints / maintenance
    """

    # ---------- Core ----------
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='tickets')
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES,
                                   db_index=True)

    # ---------- Content ----------
    subject = models.CharField(max_length=200)
    raw_input = models.TextField(help_text="Original text from student (before AI formatting).")
    formatted_body = models.TextField(blank=True,
                                      help_text="AI-formatted formal application text.")

    # ---------- Routing & Priority ----------
    assigned_department = models.CharField(max_length=30, blank=True,
                                           choices=ROUTING_DEPARTMENTS, db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='assigned_tickets')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES,
                                default=PRIORITY_MEDIUM, db_index=True)

    # ---------- Lifecycle ----------
    status = models.CharField(max_length=20, choices=TICKET_STATUS_CHOICES,
                              default=TICKET_STATUS_PENDING, db_index=True)
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='resolved_tickets')
    resolved_at = models.DateTimeField(null=True, blank=True)

    # ---------- Student Confirmation (feedback loop) ----------
    student_confirmed = models.BooleanField(null=True, blank=True,
                                            help_text="None = awaiting, True = fixed, False = reopen.")

    # ---------- Attachments ----------
    attachment = models.FileField(upload_to=ticket_attachment_path,
                                  null=True, blank=True,
                                  validators=[validate_upload_size, validate_upload_extension])

    # ---------- AI Metadata ----------
    ai_metadata = models.JSONField(default=dict, blank=True,
                                   help_text="Classifier scores, LLM responses, etc.")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['assigned_department', 'status']),
        ]

    # ---------- Computed Properties ----------
    @property
    def age_hours(self):
        """Hours from creation to now (or resolution)."""
        end = self.resolved_at or timezone.now()
        return round((end - self.created_at).total_seconds() / 3600, 2)

    @property
    def ageing_color(self):
        """Green / yellow / red based on age + status."""
        if self.status in (TICKET_STATUS_RESOLVED,):
            return 'green'
        hours = self.age_hours
        if hours < AGEING_GREEN_HOURS:
            return 'green'
        if hours < AGEING_YELLOW_HOURS:
            return 'yellow'
        return 'red'

    @property
    def is_awaiting_confirmation(self):
        return (self.status == TICKET_STATUS_RESOLVED
                and self.student_confirmed is None)

    # ---------- Convenience ----------
    def is_complaint(self):
        return self.ticket_type == TICKET_TYPE_COMPLAINT

    def is_leave(self):
        return self.ticket_type == TICKET_TYPE_LEAVE

    def is_document_request(self):
        return self.ticket_type == TICKET_TYPE_DOCUMENT

    def is_gatepass(self):
        return self.ticket_type == TICKET_TYPE_GATEPASS

    def __str__(self):
        return f"#{self.id} {self.get_ticket_type_display()} — {self.subject[:40]}"


class TicketComment(TimeStampedModel):
    """
    Conversation thread on a ticket — between student and admin.
    """
    ticket = models.ForeignKey(CampusTicket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    is_internal = models.BooleanField(default=False,
                                      help_text="Internal admin note — hidden from student.")

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on #{self.ticket.id}"