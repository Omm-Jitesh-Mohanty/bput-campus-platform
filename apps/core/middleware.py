"""
Middleware to make the current HTTP request available to signals.

Django signals (post_save, post_delete) don't receive the request.
But to audit "who did this", we need request.user, request.META, etc.

Solution: store the request in a thread-local. Signals read from it.
The middleware clears it at the end of the request to avoid leaks.
"""
import threading

_thread_locals = threading.local()


def get_current_request():
    """Return the request object for the current thread, or None."""
    return getattr(_thread_locals, 'request', None)


def get_current_user():
    """Return the authenticated user for the current thread, or None."""
    request = get_current_request()
    if request and hasattr(request, 'user'):
        if request.user.is_authenticated:
            return request.user
    return None


def get_client_ip():
    """Return the client's IP from the current request, or None."""
    request = get_current_request()
    if not request:
        return None
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_user_agent():
    """Return the User-Agent header from the current request."""
    request = get_current_request()
    if not request:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:300]


class CurrentRequestMiddleware:
    """
    Attach the current request to thread-local storage.
    Must be placed AFTER AuthenticationMiddleware in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            response = self.get_response(request)
        finally:
            # Clean up to prevent cross-request leakage in threaded servers
            _thread_locals.request = None
        return response