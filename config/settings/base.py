"""
Base settings — shared across dev and prod.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env')

# ===== SECURITY =====
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost').split(',')]

# ===== APPLICATIONS =====
DJANGO_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'django_htmx',
    'rest_framework',
    'channels', 
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.attendance',
    'apps.tickets',
    'apps.notices',
    'apps.feedback',
    'apps.documents',
    'apps.dashboard',
    'apps.manage_panel',
    'apps.workflows',
    'apps.notifications',
    'apps.chatbot.apps.ChatbotConfig',
    'apps.emergency.apps.EmergencyConfig',
    'apps.teachers',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ===== MIDDLEWARE =====
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',  
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',       # i18n
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.middleware.CurrentRequestMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'apps.accounts.middleware.DjangoAdminAccessMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ===== TEMPLATES =====
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'apps.core.context_processors.campus_config',
                'apps.core.context_processors.user_permissions_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# =========================================================
# Database Configuration
# =========================================================
# Uses Postgres by default (from .env). Falls back to SQLite
# if DB_ENGINE is explicitly set to sqlite3.

_DB_ENGINE = os.getenv('DB_ENGINE', 'django.db.backends.postgresql')

if _DB_ENGINE == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / os.getenv('DB_NAME_SQLITE', 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': _DB_ENGINE,
            'NAME': os.getenv('DB_NAME', 'campus_platform'),
            'USER': os.getenv('DB_USER', 'campus_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,           # persistent connections
            'CONN_HEALTH_CHECKS': True,    # validate before reuse
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }

# ===== AUTH =====
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ===== INTERNATIONALIZATION =====
LANGUAGE_CODE = 'en'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('hi', 'हिन्दी'),
    ('or', 'ଓଡ଼ିଆ'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

# ===== STATIC & MEDIA =====
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===== FILE UPLOAD LIMITS =====
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024        # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ===== AI ENGINE CONFIG =====
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3')
LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '30'))

EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
VECTOR_STORE_PATH = BASE_DIR / os.getenv('VECTOR_STORE_PATH', 'ai_engine/vector_store_data')

# ===== LOGGING =====
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'ai_engine': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
    },
}

# Cache static files for 1 year (only in prod)
if not DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'


# =========================================================
# Email Configuration
# =========================================================
# In dev, use console backend (prints to terminal).
# In prod, switch to SMTP.
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'Campus Platform <noreply@campus.local>'
)


# # =========================================================
# # Django Channels (WebSocket support)
# # =========================================================
# ASGI_APPLICATION = 'config.asgi.application'

# # Channel layer — Redis in all environments for consistency
# # If Redis is down, Django falls back to in-memory (dev only)
# REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             'hosts': [REDIS_URL],
#             'capacity': 1500,
#             'expiry': 10,
#         },
#     },
# }

# =========================================================
# Django Channels (WebSocket support)
# =========================================================
ASGI_APPLICATION = 'config.asgi.application'

# Redis / Memurai connection
REDIS_URL = os.getenv(
    'REDIS_URL',
    'redis://localhost:6379/0'
)

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [
                {
                    'address': REDIS_URL,
                    'socket_connect_timeout': 5,
                    'socket_timeout': None,
                }
            ],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}


# ===== SOS (Emergency Calling) =====
SOS_PROVIDER = os.getenv('SOS_PROVIDER', 'log')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM = os.getenv('TWILIO_FROM', '')
SOS_PUBLIC_BASE_URL = os.getenv('SOS_PUBLIC_BASE_URL', '')

SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000').rstrip('/')

DOC_SIGNING_SECRET = os.getenv('DOC_SIGNING_SECRET', '')