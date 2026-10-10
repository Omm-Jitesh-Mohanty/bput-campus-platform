from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    label = 'core'

    def ready(self):
        """Import signals when app is ready."""
        from . import signals  # noqa
        from . import permissions  # noqa — ensures registry is populated