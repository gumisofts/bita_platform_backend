import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv

load_dotenv(override=True)
load_dotenv(".env.production", override=True)


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", get_random_secret_key())

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

CSRF_TRUSTED_ORIGINS = os.getenv(
    "DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:3000,http://localhost:3002"
).split(",")

# Wildcard tunnel domains so dev tunnels (ngrok, cloudflared) work without
# touching .env every session. These patterns are safe because they only
# match HTTPS subdomains of the respective tunnel services.
_TUNNEL_CSRF_ORIGINS = [
    "https://*.ngrok-free.app",
    "https://*.ngrok.io",
    "https://*.trycloudflare.com",
]
CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS + _TUNNEL_CSRF_ORIGINS))

CORS_ALLOWED_ORIGINS = os.getenv(
    "DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")

# Regex-based CORS to cover any ngrok / cloudflared subdomain without
# needing to update .env when the tunnel URL rotates.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://[\w-]+\.ngrok-free\.app$",
    r"^https://[\w-]+\.ngrok\.io$",
    r"^https://[\w-]+\.trycloudflare\.com$",
]

# Allow the custom tenant-context headers sent by the frontend on every request.
# django-cors-headers defaults only cover standard headers, so custom ones must
# be listed explicitly here.
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-business-id",
    "x-branch-id",
]

AUTH_USER_MODEL = "accounts.User"

DEFAULT_APPS = [
    "admin_interface",
    "colorfield",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "corsheaders",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "drf_spectacular_sidecar",
    "django_filters",
    "guardian",
]

LOCAL_APPS = [
    "core",
    "accounts",
    "administration",
    "files",
    "storages",
    "inventories",
    "business",
    "notifications",
    "orders",
    "crms",
    "finances",
    "markets",
    "chat",
    "debug_toolbar",
]

INSTALLED_APPS = DEFAULT_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "business.middleware.BusinessContextMiddleWare",
]

ROOT_URLCONF = "core.urls"

INTERNAL_IPS = ["127.0.0.1", "0.0.0.0"]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: True,
}
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "notifications" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.impersonation_status",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.app"
ASGI_APPLICATION = "core.asgi.app"


_postgres_url = os.getenv("DJANGO_POSTGRES_URL")
if _postgres_url:
    tmpPostgres = urlparse(_postgres_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": tmpPostgres.path[1:] if tmpPostgres.path else "",
            "USER": tmpPostgres.username,
            "PASSWORD": tmpPostgres.password,
            "HOST": tmpPostgres.hostname,
            "PORT": tmpPostgres.port,
            "CONN_MAX_AGE": 60,
            "OPTIONS": dict(parse_qsl(tmpPostgres.query)),
        },
    }
else:
    # Fallback to SQLite for local development / management commands when no
    # DJANGO_POSTGRES_URL is set. Production must always provide the env var.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Addis_Ababa"

USE_I18N = True

USE_TZ = True

STORAGES = {
    "default": {
        "BACKEND": "core.storage.PublicMinIOStorage",
        "OPTIONS": {
            "bucket_name": os.getenv("AWS_STORAGE_BUCKET_NAME"),
            "region_name": os.getenv("AWS_S3_REGION_NAME"),
            "endpoint_url": os.getenv("AWS_S3_ENDPOINT_URL"),
            "querystring_auth": True,
        },
        "FILE_UPLOAD_PERMISSIONS": 0o644,
        "FILE_UPLOAD_DIRECTORY_PERMISSIONS": 0o755,
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = os.getenv("MEDIA_URL", "/medias/")
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/var/www/medias"))

if not os.getenv("AWS_STORAGE_BUCKET_NAME"):
    STORAGES["default"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": str(MEDIA_ROOT),
            "base_url": MEDIA_URL,
        },
    }

STATIC_URL = os.getenv("STATIC_URL", "/static/")
STATICFILES_DIRS = [BASE_DIR / "staticfiles"]

STATIC_ROOT = Path(os.getenv("STATIC_ROOT", "/var/www/static"))

# MEDIA_URL = "/medias/"
# MEDIA_ROOT = Path("/var/www/medias")

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = DEBUG  # Use finders in development, storage in production
WHITENOISE_AUTOREFRESH = DEBUG  # Auto-refresh in development
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0  # 1 year cache in production
WHITENOISE_MANIFEST_STRICT = not DEBUG  # Strict manifest checking in production

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "COERCE_DECIMAL_TO_STRING": False,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PERMISSION_CLASSES": [],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 10,
}

# --- Email -----------------------------------------------------------------
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# Port 465 uses implicit SSL; 587 uses STARTTLS. Pick one automatically unless
# overridden — Django raises if both EMAIL_USE_SSL and EMAIL_USE_TLS are True.
EMAIL_USE_SSL = os.getenv(
    "EMAIL_USE_SSL", "true" if EMAIL_PORT == 465 else "false"
).lower() in ("true", "1", "yes")
EMAIL_USE_TLS = os.getenv(
    "EMAIL_USE_TLS", "false" if EMAIL_USE_SSL else "true"
).lower() in ("true", "1", "yes")

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@bita.et"
)

# Use the real SMTP backend only when a host is configured and we're not in
# DEBUG; otherwise print emails (incl. verification codes) to the console so
# local development doesn't require an SMTP server.


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("DJANGO_REDIS_URL", "redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "bita_platform_backend",
    }
}

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    (
        "django.core.mail.backends.smtp.EmailBackend"
        if (EMAIL_HOST and not DEBUG)
        else "django.core.mail.backends.console.EmailBackend"
    ),
)

# Deliver email asynchronously through Celery in production; send synchronously
# in DEBUG so a running worker/broker isn't required locally.
EMAIL_USE_CELERY = os.getenv(
    "EMAIL_USE_CELERY", "false" if DEBUG else "true"
).lower() in ("true", "1", "yes")

# --- SMS ---------------------------------------------------------------
# Swappable like EMAIL_BACKEND: set SMS_BACKEND to the dotted path of any
# notifications.sms.base.BaseSmsBackend subclass. Defaults to printing to
# the console (no live provider needed) unless a real provider key is set.
SMS_ETHIOPIA_API_KEY = os.getenv("SMS_ETHIOPIA_API_KEY")
SMS_ETHIOPIA_BASE_URL = os.getenv(
    "SMS_ETHIOPIA_BASE_URL", "https://smsethiopia.et/api/sms/send"
)
SMS_BACKEND = os.getenv(
    "SMS_BACKEND",
    (
        "notifications.sms.backends.sms_ethiopia.SmsEthiopiaBackend"
        if (SMS_ETHIOPIA_API_KEY and not DEBUG)
        else "notifications.sms.backends.console.ConsoleSmsBackend"
    ),
)

# Deliver SMS asynchronously through Celery in production; send synchronously
# in DEBUG so a running worker/broker isn't required locally.
SMS_USE_CELERY = os.getenv("SMS_USE_CELERY", "false" if DEBUG else "true").lower() in (
    "true",
    "1",
    "yes",
)

ADMIN = ("Murad", "nuradhussen082@gmail.com")

CELERY_BROKER_URL = os.getenv("DJANGO_CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("DJANGO_CELERY_BACKEND_URL")

from core.celery.queues import CeleryQueue  # noqa: E402

CELERY_TASK_QUEUES = CeleryQueue.queues()
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_CREATE_MISSING_QUEUES = True


SIMPLE_JWT = {
    # Defaults match common DRF SimpleJWT recommendations. Override per-environment
    # via DJANGO_JWT_ACCESS_MINUTES / DJANGO_JWT_REFRESH_DAYS env vars when needed.
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("DJANGO_JWT_ACCESS_MINUTES", "60"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("DJANGO_JWT_REFRESH_DAYS", "30"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
}


SPECTACULAR_SETTINGS = {
    "TITLE": "API Documentation",
    "DESCRIPTION": "Description of documentation",
    "VERSION": "0.0.1",
    "SERVE_INCLUDE_SCHEMA": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "COMPONENT_SPLIT_REQUEST": True,
    "SERVERS": [
        {
            "url": "/",
            "description": "Current Development Server",
        },
        {
            "url": "http://localhost:8000",
            "description": "Local Development Server",
        },
        {
            "url": "https://apis.bita.gumisofts.com/v01",
            "description": "V01 Production Server",
        },
        {
            "url": "https://mpto2cz1lg.execute-api.eu-north-1.amazonaws.com/dev",
            "description": "Active Development Server",
        },
        {
            "url": "https://mpto2cz1lg.execute-api.eu-north-1.amazonaws.com/v01",
            "description": "Alias of V01 Production Server",
        },
    ],
}

AUTHENTICATION_BACKENDS = [
    "accounts.backends.PhoneBackend",
    "accounts.backends.EmailBackend",
    "accounts.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]


AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "eu-north-1")
AWS_S3_ENDPOINT_URL = os.getenv(
    "AWS_S3_ENDPOINT_URL", "https://s3.eu-north-1.amazonaws.com"
)
# Public URL clients receive in presigned links (MinIO behind a reverse proxy).
# When set, PublicMinIOStorage rewrites signed URLs from AWS_S3_ENDPOINT_URL
# to this value so clients never see the internal address.
AWS_S3_PUBLIC_URL = os.getenv("AWS_S3_PUBLIC_URL", "")

GOOGLE_WEB_CLIENT_ID = os.getenv("GOOGLE_WEB_CLIENT_ID")

AWS_S3_CUSTOM_DOMAIN = None

AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 3600


# Guardian settings
GUARDIAN_RAISE_403 = True
ANONYMOUS_USER_NAME = None

X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

TELEBIRR_BASE_URL = os.getenv("TELEBIRR_BASE_URL")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Public base URL of the Mini App / web frontend, used to build the
# "connect your Telegram" magic link emailed to users (no trailing slash).
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

# Public base URL of THIS backend API (no trailing slash). Used to build the
# Telegram webhook URL in the set_telegram_webhook management command.
BACKEND_URL = os.getenv("BACKEND_URL", "")

# Shared secret echoed by Telegram in the X-Telegram-Bot-Api-Secret-Token header
# on every webhook request; the webhook view rejects requests that don't match.
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
