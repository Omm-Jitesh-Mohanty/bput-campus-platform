"""
Function-based view decorators for role checks.
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_admin_role():
            raise PermissionDenied("Admin access required.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def student_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role != 'student':
            raise PermissionDenied("Student access only.")
        return view_func(request, *args, **kwargs)
    return _wrapped