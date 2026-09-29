"""
Shared test helpers.
"""
from django.contrib.auth import get_user_model
from apps.core.models import Department, TicketType, PriorityLevel, SLAPolicy

User = get_user_model()


def make_student(username='test_student', **kwargs):
    defaults = {
        'role': 'student',
        'department': 'CSE',
        'batch_year': '2023',
        'hostel_block': 'A',
        'room_number': '101',
        'password': 'testpass123',
    }
    defaults.update(kwargs)
    password = defaults.pop('password')
    user, _ = User.objects.get_or_create(username=username, defaults=defaults)
    user.set_password(password)
    user.save()
    return user


def make_admin(username='test_warden', role='warden', **kwargs):
    defaults = {
        'role': role,
        'department': 'CSE',
        'password': 'testpass123',
    }
    defaults.update(kwargs)
    password = defaults.pop('password')
    user, _ = User.objects.get_or_create(username=username, defaults=defaults)
    user.set_password(password)
    user.save()
    return user


def login(client, user):
    return client.login(username=user.username, password='testpass123')