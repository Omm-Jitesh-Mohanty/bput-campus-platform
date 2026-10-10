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

# from django.contrib.auth.models import AbstractUser
# from django.db import models
# from decimal import Decimal

# from apps.core.constants import (
#     ROLE_CHOICES, ROLE_STUDENT, ADMIN_ROLES,
#     # DEPARTMENT_CODES, BATCH_YEARS, HOSTEL_BLOCKS,
# )


# class User(AbstractUser):
#     """Custom user with campus-specific fields."""
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT, db_index=True)
#     department = models.CharField(max_length=20, blank=True, db_index=True)
#     batch_year = models.CharField(max_length=10, blank=True, db_index=True)
#     hostel_block = models.CharField(max_length=20, blank=True)
#     room_number = models.CharField(max_length=10, blank=True)
#     phone = models.CharField(max_length=15, blank=True)
#     language_pref = models.CharField(max_length=5, default='en',
#                                       choices=[('en', 'English'), ('hi', 'Hindi'), ('or', 'Odia')])
#     has_smartphone = models.BooleanField(default=True,
#                                          help_text="If False, admin can assist via SMS/print.")

#     class Meta:
#         ordering = ['username']
#         indexes = [
#             models.Index(fields=['role', 'department']),
#             models.Index(fields=['batch_year', 'hostel_block']),
#         ]

#     def is_admin_role(self):
#         return self.role in ADMIN_ROLES

#     def is_student(self):
#         return self.role == ROLE_STUDENT

#     def __str__(self):
#         return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


# class FeeRecord(models.Model):
#     """Tracks fees paid and dues per student."""
#     student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fee_records')
#     semester = models.CharField(max_length=20, help_text="e.g. '2025-ODD'")
#     total_dues = models.DecimalField(max_digits=10, decimal_places=2)
#     paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
#     due_date = models.DateField(null=True, blank=True)
#     is_cleared = models.BooleanField(default=False)
#     remarks = models.CharField(max_length=200, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ['-due_date']
#         unique_together = ('student', 'semester')

#     @property
#     def pending(self):
#         return self.total_dues - self.paid_amount

#     @property
#     def is_cleared_auto(self):
#         return self.pending <= 0

#     def __str__(self):
#         return f"{self.student.username} — {self.semester} — ₹{self.pending} pending"

from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal

from apps.core.constants import (
    ROLE_CHOICES, ROLE_STUDENT, ADMIN_ROLES,
    # DEPARTMENT_CODES, BATCH_YEARS, HOSTEL_BLOCKS,
)


class User(AbstractUser):
    """Custom user with campus-specific fields."""

    ROLE_CHOICES = [
        ('chairman', 'Chairman'),
        ('director', 'Director'),
        ('principal', 'Principal'),
        ('dean', 'Dean'),
        ('ao', 'Administrative Officer'),
        ('hod', 'HOD'),
        ('asst_prof', 'Assistant Professor'),
        ('lab_asst', 'Lab Assistant'),
        ('warden', 'Warden'),
        ('clerk', 'Office Clerk'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ]

    ROLE_HIERARCHY = {
        'chairman': 100,
        'director': 90,
        'principal': 80,
        'dean': 70,
        'ao': 65,
        'hod': 60,
        'warden': 55,
        'asst_prof': 50,
        'teacher': 48,
        'lab_asst': 40,
        'clerk': 35,
        'student': 10,
    }

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student',
        db_index=True
    )

    # --- Scoping fields ---
    department = models.CharField(
        max_length=20,
        blank=True,
        db_index=True
    )

    batch_year = models.CharField(
        max_length=10,
        blank=True,
        db_index=True
    )

    hostel_block = models.CharField(
        max_length=20,
        blank=True
    )

    room_number = models.CharField(
        max_length=10,
        blank=True
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    language_pref = models.CharField(
        max_length=5,
        default='en',
        choices=[
            ('en', 'English'),
            ('hi', 'Hindi'),
            ('or', 'Odia')
        ]
    )

    has_smartphone = models.BooleanField(
        default=True
    )

    # --- Hierarchy links ---
    reports_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='direct_reports',
        help_text="Direct supervisor in the organization"
    )

    # --- SOS fields ---
    emergency_contacts = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of {name, phone, relation, priority} for emergency SOS. "
            "Priority 1 is called first, then 2, then 3..."
        )
    )

    class Meta:
        ordering = ['-role', 'username']
        indexes = [
            models.Index(fields=['role', 'department']),
            models.Index(fields=['role', 'hostel_block']),
            models.Index(fields=['batch_year']),
        ]

    def is_admin_role(self):
        """Any non-student role."""
        return self.role != 'student'

    def is_student(self):
        return self.role == 'student'

    def role_rank(self):
        """Higher number = more authority."""
        return self.ROLE_HIERARCHY.get(self.role, 0)

    def has_rank_at_least(self, role):
        """Is this user's role at least as authoritative as `role`?"""
        return self.role_rank() >= self.ROLE_HIERARCHY.get(role, 0)

    def scope_summary(self):
        """
        Return a human-readable description of what this user can see.
        Used in admin UI to help supervisors understand roles.
        """
        if self.role in ('chairman', 'director', 'principal'):
            return "Full campus"

        if self.role == 'dean':
            return "All departments (academic)"

        if self.role == 'ao':
            return "Administration-wide"

        if self.role == 'hod':
            return f"Department {self.department or '?'}"

        if self.role == 'warden':
            return f"Hostel Block {self.hostel_block or '?'}"

        if self.role in ('asst_prof', 'teacher', 'lab_asst'):
            return f"Dept {self.department or '?'}"

        if self.role == 'clerk':
            return "Front office (read-only)"

        return "Personal only"

    def home_redirect(self):
        """Return the appropriate home URL for this user's role."""
        from django.urls import reverse

        if self.role == 'student':
            return reverse('dashboard:student_home')

        if self.role in ('principal', 'director', 'chairman'):
            return reverse('dashboard:executive')

        if self.role in ('warden', 'hod', 'dean', 'ao', 'clerk'):
            return reverse('tickets:my_queue')

        return reverse('dashboard:home_router')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class FeeRecord(models.Model):
    """Tracks fees paid and dues per student."""

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fee_records'
    )

    semester = models.CharField(
        max_length=20,
        help_text="e.g. '2025-ODD'"
    )

    total_dues = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    due_date = models.DateField(
        null=True,
        blank=True
    )

    is_cleared = models.BooleanField(
        default=False
    )

    remarks = models.CharField(
        max_length=200,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

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