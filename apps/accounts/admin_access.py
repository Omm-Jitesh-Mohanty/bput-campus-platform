"""
Custom admin site permissions for Django admin.
"""
from django.contrib.admin import AdminSite


class RestrictedAdminSite(AdminSite):
    """Only superusers and top-tier roles can access Django admin."""

    def has_permission(self, request):
        if not request.user.is_active:
            return False
        if request.user.is_superuser:
            return True
        # Only chairman and director
        return request.user.role in ('chairman', 'director')


restricted_admin_site = RestrictedAdminSite(name='restricted_admin')