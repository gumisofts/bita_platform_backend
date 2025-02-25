import os
from datetime import timedelta
from pathlib import Path

from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes

load_dotenv()
load_dotenv(".env.production", override=True)
env = os.getenv


BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = env("SECRET_KEY", get_random_secret_key())

DEBUG = env("DEBUG", False) == "True"

ALLOWED_HOSTS = env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")


# Application definition

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")

AUTH_USER_MODEL = "accounts.User"
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "drf_spectacular_sidecar",
    "accounts",
    "file",
    "storages",
    "notification",
    "inventory",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["notification.templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.app"
ASGI_APPLICATION = "core.asgi.app"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "prod": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("PG_DB_NAME", "dev"),
        "USER": env("PG_USER", "dev"),
        "PASSWORD": env("PG_PASSWORD", "developer@123"),
        "HOST": env("PG_HOST", "localhost"),
        "PORT": env("PG_PORT", "5432"),
        "CONN_MAX_AGE": None,
        "OPTIONS": {"sslmode": env("PG_SSL_MODE")},
    },
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

EMAIL_USE_TLS = True
EMAIL_BACKEND = "django_smtp_ssl.SSLEmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")

ADMIN = ("Murad", "nuradhussen082@gmail.com")

CELERY_BROKER_URL = f"redis://{env('REDIS_USERNAME','default')}:{env('REDIS_PASSWORD','')}@{env('REDIS_HOST','localhost')}:{env('REDIS_PORT',6379)}"
CELERY_BACKEND_URL = f"redis://{env('REDIS_USERNAME','default')}:{env('REDIS_PASSWORD','')}@{env('REDIS_HOST','localhost')}:{env('REDIS_PORT',6379)}"


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=90),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=90),
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
    # OTHER SETTINGS
    "SWAGGER_UI_DIST": "SIDECAR",  # shorthand to use the sidecar instead
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    # for binary data upload support
    "COMPONENT_SPLIT_REQUEST": True,
}

AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailOrPhoneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# TODO Remove these
EMAIL_URL = ""
NOTIFICATION_API_KEY = ""


# AWS Credentials
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")

# S3 Storage Configuration
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

# Drf-Spectacular Additional Settings
ITEM_LIST_QUERY_PARAMETERS = [
    OpenApiParameter(
        name="category_id",
        description="Filter by category ID",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="manufacturer_id",
        description="Filter by manufacturer ID",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="visible",
        description="Filter by visibility (true/false)",
        required=False,
        type=OpenApiTypes.BOOL,
    ),
    OpenApiParameter(
        name="returnable",
        description="Filter by returnable (true/false)",
        required=False,
        type=OpenApiTypes.BOOL,
    ),
    OpenApiParameter(
        name="search",
        description="Search term",
        required=False,
        type=OpenApiTypes.STR,
    ),
]

SUPPLY_RESERVATION_LIST_QUERY_PARAMETERS = [
    OpenApiParameter(
        name="status",
        description="Filter by reservation status (active, cancelled, fulfilled)",
        required=False,
        type=OpenApiTypes.STR,
    ),
]
