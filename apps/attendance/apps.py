# from django.apps import AppConfig


# class AttendanceConfig(AppConfig):
#     default_auto_field = "django.db.models.BigAutoField"
#     name = "apps.attendance"
#     label = 'attendance'
from django.apps import AppConfig


class AttendanceConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.attendance"

    label = 'attendance'

    def ready(self):
        from . import signals  # noqa