# from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel
# from apps.core.constants import DEPARTMENT_CODES, BATCH_YEARS


class AttendanceRecord(TimeStampedModel):
    """Subject-wise attendance for a student."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_records',
    )
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=100)
    total_classes = models.PositiveIntegerField(default=0)
    attended_classes = models.PositiveIntegerField(default=0)
    faculty_name = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['subject_name']
        unique_together = ('student', 'subject_code')

    @property
    def percentage(self):
        if self.total_classes == 0:
            return 0.0
        return round(
            (self.attended_classes / self.total_classes) * 100,
            2,
        )

    @property
    def is_below_threshold(self):
        from apps.core.services import ConfigService
        return (
            self.percentage
            < ConfigService.get_attendance_threshold()
        )

    def __str__(self):
        return (
            f"{self.student.username} — "
            f"{self.subject_name} — "
            f"{self.percentage}%"
        )


class Timetable(TimeStampedModel):
    """Class schedule for a department + batch."""

    DAYS = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
    ]

    department = models.CharField(max_length=20)
    batch_year = models.CharField(max_length=10)
    day_of_week = models.CharField(
        max_length=3,
        choices=DAYS,
    )
    time_slot = models.CharField(
        max_length=20,
        help_text="e.g. '10:00-11:00'",
    )
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=100)
    faculty_name = models.CharField(
        max_length=100,
        blank=True,
    )
    room = models.CharField(
        max_length=20,
        blank=True,
    )

    is_cancelled = models.BooleanField(default=False)
    cancel_reason = models.CharField(
        max_length=200,
        blank=True,
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['day_of_week', 'time_slot']
        indexes = [
            models.Index(
                fields=[
                    'department',
                    'batch_year',
                    'day_of_week',
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.department} {self.batch_year} — "
            f"{self.day_of_week} {self.time_slot} — "
            f"{self.subject_name}"
        )


class ClassCancellation(TimeStampedModel):
    """A cancellation of a scheduled class."""

    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.CASCADE,
        related_name='cancellations',
    )
    date = models.DateField(db_index=True)
    reason = models.CharField(
        max_length=200,
        blank=True,
    )
    announced_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    replacement_slot = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional: rescheduled time",
    )

    class Meta:
        unique_together = ('timetable', 'date')
        ordering = ['-date']


class StudentRoutine(TimeStampedModel):
    """
    Personal routine preferences and the day's computed plan.
    """

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='routine',
    )
    study_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "e.g. {'preferred_study_hours': "
            "['18:00-20:00'], "
            "'weak_subjects': ['CS301']}"
        ),
    )
    daily_plan = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of today's computed plan",
    )
    last_computed = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Routine: {self.student.username}"