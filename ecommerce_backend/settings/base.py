# ecommerce_backend/settings/base.py


import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
import environ
import structlog
from structlog.stdlib import ProcessorFormatter

# Initialize environ
env = environ.Env(
    # Set casting and default values
    SECRET_KEY=(str, "SECRET_KEY"),
    DEBUG=(bool, "DEBUG"),
    DJANGO_ALLOWED_HOSTS=(
        list,
        ["localhost", "127.0.0.1", "project-nexus-backend-q5ai.onrender.com"],
    ),
    DATABASE_URL=(str, "DATABASE_URL"),
    DB_ENGINE=(str, "DB_ENGINE"),
    DB_NAME=(str, "DB_NAME"),
    DB_USER=(str, "DB_USER"),
    DB_PASSWORD=(str, "DB_PASSWORD"),
    DB_HOST=(str, "DB_HOST"),
    DB_PORT=(str, "DB_PORT"),
    EMAIL_HOST=(str, "EMAIL_HOST"),
    EMAIL_PORT=(int, "EMAIL_PORT"),
    EMAIL_USE_TLS=(bool, "EMAIL_USE_TLS"),
    EMAIL_HOST_USER=(str, "EMAIL_HOST_USER"),
    EMAIL_HOST_PASSWORD=(str, "EMAIL_HOST_PASSWORD"),
    DEFAULT_FROM_EMAIL=(str, "DEFAULT_FROM_EMAIL"),
    SERVER_EMAIL=(str, "SERVER_EMAIL"),
    FRONTEND_URL=(str, "FRONTEND_URL"),
    SITE_NAME=(str, "SITE_NAME"),
    SITE_DOMAIN=(str, "SITE_DOMAIN"),
    CORS_ALLOWED_ORIGINS=(list, ["CORS_ALLOWED_ORIGINS"]),
    SESSION_ENGINE=(str, "django.contrib.sessions.backends.cache"),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SESSION_EXPIRE_AT_BROWSER_CLOSE=(bool, False),
    SESSION_COOKIE_AGE=(int, "SESSION_COOKIE_AGE"),
    REDIS_URL=(str, "REDIS_URL"),
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Create necessary directories if they don't exist
directories_to_create = ["logs", "static", "media"]
for directory in directories_to_create:
    (BASE_DIR / directory).mkdir(exist_ok=True)

# Take environment variables from .env file
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

# ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
# Determine allowed hosts based on environment
if os.environ.get("RENDER"):
    # Production on Render
    ALLOWED_HOSTS = [
        "project-nexus-backend-q5ai.onrender.com",
        ".onrender.com",
    ]
else:
    # Local development
    ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # For PostgreSQL index feature
    # Third-party apps
    "corsheaders",
    "django_filters",
    "django_celery_beat",
    "drf_spectacular",
    "drf_spectacular_sidecar",  # Required for production schema collection
    "graphene_django",
    "django_redis",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    # Local apps
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # CORS Middleware
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.CurrentUserMiddleware",  # Current User Middleware
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.gzip.GZipMiddleware",
]

ROOT_URLCONF = "ecommerce_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ecommerce_backend.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases


# Helper function for database detection
def get_database_config():
    """Configure database based on environment with proper fallbacks"""
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        # Production/Render environment - use DATABASE_URL
        config = dj_database_url.parse(database_url, conn_max_age=600)
        # Add SSL requirement for production PostgreSQL
        config["OPTIONS"] = config.get("OPTIONS", {})
        config["OPTIONS"]["sslmode"] = "require"
        return {"default": config}

    # Local development
    db_engine = env("DB_ENGINE")

    if db_engine == "sqlite3":
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }
    else:
        # Local PostgreSQL
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": env("DB_NAME"),
                "USER": env("DB_USER"),
                "PASSWORD": env("DB_PASSWORD"),
                "HOST": env("DB_HOST"),
                "PORT": env("DB_PORT"),
                "OPTIONS": {
                    "connect_timeout": 60,
                },
            }
        }


# Database Configuration
DATABASES = get_database_config()

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailBackend",  # Custom email auth backend
    "django.contrib.auth.backends.ModelBackend",  # Default Django auth backend
]

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Session settings
SESSION_ENGINE = env.str("SESSION_ENGINE")
SESSION_CACHE_ALIAS = "sessions"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE")
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool("SESSION_EXPIRE_AT_BROWSER_CLOSE")
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE")

# Cache settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "ecommerce",
    },
    "sessions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/2"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "ecommerce_sessions",
    },
}

# Celery Configuration
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True


# Email Backend Configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
SERVER_EMAIL = env("SERVER_EMAIL")

# Frontend URL for password reset links
FRONTEND_URL = env("FRONTEND_URL")

# Site information
SITE_NAME = env("SITE_NAME")
SITE_DOMAIN = env("SITE_DOMAIN")

# Password reset timeout (in seconds, 24 hours)
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24  # 24 hours

# Authentication URLs
LOGIN_URL = "/api/v1/accounts/login/"

# Rest Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.core.throttling.CustomUserRateThrottle",
        "apps.core.throttling.CustomAnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",  # 100 requests per hour
        "user": "1000/hour",  # 1000 requests per hour
        "admin": "5000/hour",  # 5000 requests per hour
        "burst": "60/min",  # 60 requests per minute
        "login": "10/hour",  # 10 login attempts per hour
        "register": "5/hour",  # 5 registrations per hour
        "password_reset": "3/hour",  # 3 password resets per hour
        "api_key": "2000/hour",  # 2000 requests per hour for API keys
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# Enable Browsable API in development
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += [
        "rest_framework.renderers.BrowsableAPIRenderer",
    ]

# CORS Configuration
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# Allow CORS for all origins in development
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_CREDENTIALS = True

# JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=240),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
}

# Swagger/OpenAPI Configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "ALX E-Commerce API",
    "DESCRIPTION": "Comprehensive e-commerce backend API with REST and GraphQL support",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
}

# GraphQL Configuration
GRAPHENE = {
    "SCHEMA": "ecommerce_backend.schema.schema",
    "MIDDLEWARE": [
        "apps.core.middleware.PerformanceMiddleware",
    ],
}


# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "debug.log"),
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": True,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}


_PRE_CHAIN = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
]

# Add a JSON formatter for structlog -> stdlib
LOGGING["formatters"]["json"] = {
    "()": ProcessorFormatter,
    "processor": structlog.processors.JSONRenderer(),
    "foreign_pre_chain": _PRE_CHAIN,
}

# Use JSON on console (stdout); keep file handler as-is
LOGGING["handlers"]["console"]["formatter"] = "json"

# Ensure the root logger sends to console (JSON)
LOGGING["root"] = {
    "handlers": ["console"],
    "level": "INFO",
}

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
