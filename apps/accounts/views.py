# from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.translation import activate
from django.contrib import messages

from .forms import LoginForm


def login_view(request):
    """Handle login for both students and admins."""
    if request.user.is_authenticated:
        return redirect('accounts:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # Activate user's preferred language
                if user.language_pref:
                    activate(user.language_pref)
                messages.success(request, f"Welcome back, {user.get_short_name() or user.username}!")
                return redirect('accounts:home')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Log out and return to login page."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login')


@login_required
def home_view(request):
    """
    Smart router:
      - Students → student dashboard
      - Admins   → admin dashboard
    """
    if request.user.is_admin_role():
        return redirect('dashboard:admin_home')
    return redirect('dashboard:student_home')


@login_required
def toggle_lite_mode(request):
    """Toggle lite mode for the current session."""
    request.session['lite_mode'] = not request.session.get('lite_mode', False)
    return redirect(request.META.get('HTTP_REFERER', 'accounts:home'))