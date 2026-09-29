# from django.db import models

# Create your models here.

"""
Notification models.

A Notification is an in-app message for a specific user.
It may also have been delivered via email/SMS — we track those
in the delivery_logs JSONField.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    """
    In-app notification for a user.

    Every notification has a channel-agnostic record (this table).
    Delivery attempts per channel are logged in `delivery_logs`.
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    event_code = models.CharField(
        max_length=60, db_index=True,
        help_text="e.g., 'ticket.created', 'step.approved'"
    )

    title = models.CharField(max_length=200)
    body = models.TextField()

    # Link to relevant object
    target_model = models.CharField(max_length=100, blank=True, db_index=True)
    target_id = models.CharField(max_length=50, blank=True)
    link_url = models.CharField(max_length=500, blank=True,
                                help_text="Where clicking the notification should take the user")

    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='normal', db_index=True
    )
    icon = models.CharField(max_length=10, default='🔔')

    # Read state
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Delivery tracking per channel
    delivery_logs = models.JSONField(
        default=dict, blank=True,
        help_text="{'email': {'sent': True, 'at': '...', 'error': None}, ...}"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['event_code', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.event_code}] → {self.recipient.username}: {self.title[:50]}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])


class NotificationPreference(TimeStampedModel):
    """
    Per-user channel preferences.
    If a row doesn't exist, defaults apply.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Global toggles
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)   # opt-in
    in_app_enabled = models.BooleanField(default=True)

    # Event-type toggles (JSON: {'ticket.created': True, 'notice.published': False})
    event_preferences = models.JSONField(
        default=dict, blank=True,
        help_text="Per-event overrides"
    )

    # Quiet hours (no SMS during these hours)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f"Prefs: {self.user.username}"

    def wants_event(self, event_code):
        """Return True if user wants to receive this event type."""
        if event_code in self.event_preferences:
            return bool(self.event_preferences[event_code])
        return True  # opt-out model — default is yes

    @classmethod
    def for_user(cls, user):
        """Get or create preferences for a user."""
        prefs, _ = cls.objects.get_or_create(user=user)
        return prefs
