# from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel
from apps.core.constants import DEPARTMENT_CODES, BATCH_YEARS


class AttendanceRecord(TimeStampedModel):
    """Subject-wise attendance for a student."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='attendance_records')
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
        return round((self.attended_classes / self.total_classes) * 100, 2)

    @property
    def is_below_threshold(self):
        return self.percentage < 75.0

    def __str__(self):
        return f"{self.student.username} — {self.subject_name} — {self.percentage}%"


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
    day_of_week = models.CharField(max_length=3, choices=DAYS)
    time_slot = models.CharField(max_length=20, help_text="e.g. '10:00-11:00'")
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=100)
    faculty_name = models.CharField(max_length=100, blank=True)
    room = models.CharField(max_length=20, blank=True)

    is_cancelled = models.BooleanField(default=False)
    cancel_reason = models.CharField(max_length=200, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['day_of_week', 'time_slot']
        indexes = [
            models.Index(fields=['department', 'batch_year', 'day_of_week']),
        ]

    def __str__(self):
        return f"{self.department} {self.batch_year} — {self.day_of_week} {self.time_slot} — {self.subject_name}"


class ClassCancellation(TimeStampedModel):
    """
    Log of day-specific cancellations (overrides regular timetable slot).
    Enables 'class cancelled today' notices without mutating timetable.
    """
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE,
                                  related_name='cancellations')
    date = models.DateField(db_index=True)
    reason = models.CharField(max_length=200, blank=True)
    announced_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True)

    class Meta:
        unique_together = ('timetable', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.timetable} cancelled on {self.date}"
