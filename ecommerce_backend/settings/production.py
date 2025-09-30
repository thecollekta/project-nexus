# ecommerce_backend/settings/production.py

from pathlib import Path

from .base import *  # noqa: F403

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Core settings
DEBUG = False
ENVIRONMENT = env("ENVIRONMENT", default="production")  # type: ignore # noqa: F405

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"

# Session settings for production
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "sessions"  # Point to the sessions cache
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_USE_SESSIONS = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# Email settings for production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", 587)  # type: ignore # noqa: F405
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", True)  # type: ignore # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")  # noqa: F405
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")  # noqa: F405
SERVER_EMAIL = env("SERVER_EMAIL")  # noqa: F405

# Cache settings for production (optimized for production)
CACHES["default"]["OPTIONS"].update(  # noqa: F405
    {
        "SOCKET_CONNECT_TIMEOUT": 5,
        "SOCKET_TIMEOUT": 5,
        "CONNECTION_POOL_KWARGS": {"max_connections": 100},
    }
)

# Add Redis password if provided
redis_password = env("REDIS_PASSWORD", default=None)  # type: ignore # noqa: F405
if redis_password:
    CACHES["default"]["OPTIONS"]["PASSWORD"] = redis_password  # noqa: F405

# Celery settings for production
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes


# Static and media files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MAX_AGE = 31536000  # 1 year cache for static files

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_ALLOW_ALL_ORIGINS = True

# Monitoring
ENABLE_METRICS = env.bool("ENABLE_METRICS", default=False)  # type: ignore # noqa: F405
if ENABLE_METRICS:
    INSTALLED_APPS += ["django_prometheus"]  # noqa: F405
    # MIDDLEWARE = (
    #     ["django_prometheus.middleware.PrometheusBeforeMiddleware"]
    #     + MIDDLEWARE  # noqa: F405
    #     + ["django_prometheus.middleware.PrometheusAfterMiddleware"]
    # )


# Admin URL
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")  # type: ignore # noqa: F405


# Performance optimizations
TEMPLATES[0]["OPTIONS"]["debug"] = False  # noqa: F405

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
