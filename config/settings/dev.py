"""
Development settings. Run: python manage.py runserver --settings=config.settings.dev
Default via manage.py: config.settings.dev
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# SQLite for quick dev
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Show emails in console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable password validation minimum length in dev (optional)
AUTH_PASSWORD_VALIDATORS = []

# Cache: local memory
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}