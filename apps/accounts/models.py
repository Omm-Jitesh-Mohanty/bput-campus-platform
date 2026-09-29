# # from django.db import models

# # Create your models here.
# from django.contrib.auth.models import AbstractUser
# from django.db import models


# class User(AbstractUser):
#     ROLE_CHOICES = [
#         ('student', 'Student'),
#         ('teacher', 'Teacher'),
#         ('warden', 'Warden'),
#         ('hod', 'HOD'),
#         ('dean', 'Dean'),
#         ('principal', 'Principal'),
#     ]
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
#     department = models.CharField(max_length=50, blank=True)
#     batch_year = models.CharField(max_length=10, blank=True)
#     hostel_block = models.CharField(max_length=20, blank=True)
#     room_number = models.CharField(max_length=10, blank=True)
#     phone = models.CharField(max_length=15, blank=True)
#     language_pref = models.CharField(max_length=5, default='en')

#     def is_admin_role(self):
#         return self.role in ['teacher', 'warden', 'hod', 'dean', 'principal']

#     def __str__(self):
#         return f"{self.username} ({self.role})"

from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal

from apps.core.constants import (
    ROLE_CHOICES, ROLE_STUDENT, ADMIN_ROLES,
    # DEPARTMENT_CODES, BATCH_YEARS, HOSTEL_BLOCKS,
)


class User(AbstractUser):
    """Custom user with campus-specific fields."""
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT, db_index=True)
    department = models.CharField(max_length=20, blank=True, db_index=True)
    batch_year = models.CharField(max_length=10, blank=True, db_index=True)
    hostel_block = models.CharField(max_length=20, blank=True)
    room_number = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    language_pref = models.CharField(max_length=5, default='en',
                                      choices=[('en', 'English'), ('hi', 'Hindi'), ('or', 'Odia')])
    has_smartphone = models.BooleanField(default=True,
                                         help_text="If False, admin can assist via SMS/print.")

    class Meta:
        ordering = ['username']
        indexes = [
            models.Index(fields=['role', 'department']),
            models.Index(fields=['batch_year', 'hostel_block']),
        ]

    def is_admin_role(self):
        return self.role in ADMIN_ROLES

    def is_student(self):
        return self.role == ROLE_STUDENT

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class FeeRecord(models.Model):
    """Tracks fees paid and dues per student."""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fee_records')
    semester = models.CharField(max_length=20, help_text="e.g. '2025-ODD'")
    total_dues = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    due_date = models.DateField(null=True, blank=True)
    is_cleared = models.BooleanField(default=False)
    remarks = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-due_date']
        unique_together = ('student', 'semester')

    @property
    def pending(self):
        return self.total_dues - self.paid_amount

    @property
    def is_cleared_auto(self):
        return self.pending <= 0

    def __str__(self):
        return f"{self.student.username} — {self.semester} — ₹{self.pending} pending"

