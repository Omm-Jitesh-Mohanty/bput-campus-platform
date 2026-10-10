# from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class EmergencyContact(TimeStampedModel):
    """A contact to call in an emergency."""
    RELATIONS = [
        ('parent', 'Parent'),
        ('guardian', 'Guardian'),
        ('warden', 'Warden'),
        ('friend', 'Friend'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emergency_contact_records'
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    relation = models.CharField(max_length=20, choices=RELATIONS)
    priority = models.PositiveSmallIntegerField(
        default=1,
        help_text="1 = called first, 2 = next, etc."
    )

    class Meta:
        ordering = ['priority']
        unique_together = ('user', 'phone')

    def __str__(self):
        return f"{self.name} ({self.relation}) — {self.phone}"


class EmergencyAlert(TimeStampedModel):
    """A triggered SOS."""
    STATUS_CHOICES = [
        ('triggered', 'Triggered'),
        ('calling', 'Calling contacts'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('failed', 'Failed'),
    ]
    TRIGGER_TYPES = [
        ('sos_button', 'SOS Button'),
        ('medical', 'Medical'),
        ('fire', 'Fire'),
        ('safety', 'Personal Safety'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emergency_alerts'
    )
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPES, default='sos_button')
    reason = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='triggered')
    location = models.CharField(max_length=200, blank=True)

    # Tracking
    call_log = models.JSONField(
        default=list, blank=True,
        help_text="[{'contact_name': ..., 'phone': ..., 'status': ..., 'at': ...}]"
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    # Resolution
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"SOS #{self.id} — {self.user.username} ({self.status})"