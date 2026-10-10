# apps/accounts/middleware.py
from django.core.exceptions import PermissionDenied


class DjangoAdminAccessMiddleware:
    """
    Block access to /admin/ unless the user is superuser or top-tier.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if not request.user.is_authenticated:
                pass  # let Django redirect to login
            elif not (request.user.is_superuser or
                      request.user.role in ('chairman', 'director')):
                raise PermissionDenied(
                    "Django admin is restricted to Chairman and Director."
                )
        return self.get_response(request)