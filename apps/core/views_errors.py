from django.shortcuts import redirect, render


def permission_denied_view(request, exception):
    """Custom 403 handler."""
    if request.user.is_authenticated:
        if hasattr(request.user, 'home_redirect'):
            return redirect(request.user.home_redirect())
        return redirect('home')

    return redirect('accounts:login')


def page_not_found_view(request, exception):
    """Custom 404 handler."""
    return render(request, 'errors/404.html', status=404)


def server_error_view(request):
    """Custom 500 handler."""
    return render(request, 'errors/500.html', status=500)