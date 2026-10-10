"""
Homepage — login required.
"""

from django.shortcuts import render, redirect


def home_page(request):
    """
    If not logged in → redirect to login.
    If logged in → show homepage as the landing page.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    return render(request, 'home.html', {
        'logged_in': True,
    })