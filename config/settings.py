import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'drf_yasg',
    'corsheaders',

    # Local apps
    'apps.core',
    'apps.polls',
    'apps.payments',
    'apps.compliance',
    'apps.analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'apps.core.middleware.ResponseEnvelopeMiddleware',
    'apps.compliance.middleware.GeoRestrictionMiddleware',
    'apps.compliance.middleware.ComplianceLoggingMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': BASE_DIR / 'db.sqlite3',
        # MySQL settings for production
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        } if os.environ.get('DB_ENGINE') == 'django.db.backends.mysql' else {},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'core.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.core.authentication.CachedBlacklistJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'votes': os.environ.get('THROTTLE_VOTES', '30/min'),
        'anon': os.environ.get('THROTTLE_ANON', '200/min'),
        'user': os.environ.get('THROTTLE_USER', '500/min'),
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'BLACKLIST_CHECKS': True,
}

CORS_ALLOW_ALL_ORIGINS = True

# Cache / Redis
USE_REDIS = os.environ.get('USE_REDIS') == '1'
if USE_REDIS:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'pollarize',
            'TIMEOUT': 300,  # 5 minutes default
        }
    }
else:
    # Fallback to database cache for PythonAnywhere free tier
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
            'KEY_PREFIX': 'pollarize',
            'TIMEOUT': 300,
        }
    }

# Session configuration for PythonAnywhere
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = False

# File uploads configuration
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Payment settings
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', '')
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', '')

# Analytics and Compliance settings
GEOLOCATION_PROVIDERS = [
    {
        'name': 'ipapi.co',
        'url': 'https://ipapi.co/{ip}/json/',
        'timeout': 3,
        'rate_limit': 1000,  # requests per day
    },
    {
        'name': 'ip-api.com',
        'url': 'http://ip-api.com/json/{ip}',
        'timeout': 3,
        'rate_limit': 45,  # requests per minute
    }
]

# Analytics settings
ANALYTICS_RETENTION_DAYS = int(
    os.environ.get('ANALYTICS_RETENTION_DAYS', '365'))
ANALYTICS_BATCH_SIZE = int(os.environ.get('ANALYTICS_BATCH_SIZE', '1000'))

# Compliance settings
COMPLIANCE_LOG_RETENTION_DAYS = int(
    os.environ.get('COMPLIANCE_LOG_RETENTION_DAYS', '180'))
ENABLE_GEO_RESTRICTIONS = os.environ.get('ENABLE_GEO_RESTRICTIONS', '1') == '1'

# Celery Configuration (optional for background tasks)
CELERY_BROKER_URL = os.environ.get(
    'CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get(
    'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Celery Beat Schedule (for periodic tasks)
CELERY_BEAT_SCHEDULE = {
    'update-analytics-hourly': {
        'task': 'apps.analytics.tasks.aggregate_hourly_analytics',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-old-events-daily': {
        'task': 'apps.analytics.tasks.cleanup_old_analytics_events',
        'schedule': 86400.0,  # Every day
    },
    'cleanup-compliance-logs-weekly': {
        'task': 'apps.compliance.tasks.cleanup_old_compliance_logs',
        'schedule': 604800.0,  # Every week
    },
    'cleanup-geo-cache-daily': {
        'task': 'apps.compliance.tasks.cleanup_expired_geolocation_cache',
        'schedule': 86400.0,  # Every day
    },
}

# PythonAnywhere specific settings
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.pythonanywhere.com',
    '.herokuapp.com',
    os.environ.get('DJANGO_ALLOWED_HOST', ''),
]

# Remove empty hosts
ALLOWED_HOSTS = [host for host in ALLOWED_HOSTS if host]

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Logging configuration
if DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'apps.payments': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
        },
    }
