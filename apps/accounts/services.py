"""
Business logic for user management.
Views call these — never put heavy logic directly in views.
"""
from django.contrib.auth import get_user_model

User = get_user_model()


def create_student(username, password, **extra):
    """Create a student with required role."""
    return User.objects.create_user(
        username=username,
        password=password,
        role='student',
        **extra
    )


def create_admin(username, password, role, **extra):
    """Create an admin-level user (teacher/warden/hod/dean/principal)."""
    assert role in ['teacher', 'warden', 'hod', 'dean', 'principal'], \
        f"Invalid admin role: {role}"
    return User.objects.create_user(
        username=username,
        password=password,
        role=role,
        is_staff=True,   # can log into admin panel
        **extra
    )


def get_students_in_context(department=None, batch_year=None, hostel_block=None):
    """Return filtered students for targeted notifications."""
    qs = User.objects.filter(role='student')
    if department:
        qs = qs.filter(department=department)
    if batch_year:
        qs = qs.filter(batch_year=batch_year)
    if hostel_block:
        qs = qs.filter(hostel_block=hostel_block)
    return qs