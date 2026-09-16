"""
Reusable view mixins for role-based access control.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class AdminRequiredMixin(LoginRequiredMixin):
    """Only allow users with admin-level roles (teacher, warden, hod, dean, principal)."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not request.user.is_admin_role():
            raise PermissionDenied("Admin access required.")
        return super().dispatch(request, *args, **kwargs)


class StudentRequiredMixin(LoginRequiredMixin):
    """Only allow students."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role != 'student':
            raise PermissionDenied("Student access only.")
        return super().dispatch(request, *args, **kwargs)