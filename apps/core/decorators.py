"""Role-based view decorators."""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def role_required(*roles):
    """
    Require the user to have one of the specified roles.

    Usage:
        @role_required('principal', 'director', 'chairman')
        def super_secret_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied(
                    f"This action requires one of: {', '.join(roles)}"
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def rank_required(minimum_role):
    """
    Require the user to have at least the rank of `minimum_role`.

    Example: @rank_required('dean') allows dean, principal, director, chairman.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not request.user.has_rank_at_least(minimum_role):
                raise PermissionDenied(
                    f"This action requires rank of {minimum_role} or higher."
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def admin_required(view_func):
    """Any non-student."""
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


def audit_access_required(view_func):
    """Only top-tier roles can view audit trails."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        from apps.core.scoping import DataScope
        if not DataScope.can_view_audit(request.user):
            raise PermissionDenied(
                "Audit trail access is restricted to Chairman, Director, and Principal."
            )
        return view_func(request, *args, **kwargs)
    return _wrapped