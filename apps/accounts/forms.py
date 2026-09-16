from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginForm(forms.Form):
    """Simple login form (username + password)."""
    username = forms.CharField(max_length=150, widget=forms.TextInput(
        attrs={'placeholder': 'Username', 'autofocus': True, 'class': 'form-input'}))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={'placeholder': 'Password', 'class': 'form-input'}))