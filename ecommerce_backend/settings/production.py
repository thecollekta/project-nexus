# ecommerce_backend/settings/production.py

from pathlib import Path

from .base import *  # noqa: F403

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Core settings
DEBUG = False

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

# Cache configuration for production
redis_url = env("REDIS_URL")  # noqa: F405

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": redis_url,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,
            "PASSWORD": env(  # noqa: F405
                "REDIS_PASSWORD", default=None # type: ignore
            ),  # noqa: F405 # type: ignore
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
        },
        "KEY_PREFIX": "ecommerce",
    },
    "sessions": {  # Add this missing sessions cache
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": redis_url,  # Use same Redis instance, different logical database
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,
            "PASSWORD": env(  # noqa: F405
                "REDIS_PASSWORD", default=None # type: ignore
            ),  # noqa: F405 # type: ignore
        },
        "KEY_PREFIX": "ecommerce_sessions",
    },
}

# Session settings for production
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "sessions"  # Point to the sessions cache
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_USE_SESSIONS = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 1209600  # 2 weeks

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


# Performance
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# Static and media files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

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

# Custom settings
INTERNAL_IPS = env.list("INTERNAL_IPS", default=["127.0.0.1"])  # type: ignore # noqa: F405


# Admin URL
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")  # type: ignore # noqa: F405

# Sentry configuration (if using)
# if "SENTRY_DSN" in env:  # noqa: F405
#     import sentry_sdk  # type: ignore
#     from sentry_sdk.integrations.django import DjangoIntegration  # type: ignore

#     sentry_sdk.init(
#         dsn=env("SENTRY_DSN"),  # noqa: F405
#         integrations=[DjangoIntegration()],
#         send_default_pii=True,
#         environment=env(  # noqa: F405 # type: ignore
#             "ENVIRONMENT",
#             default="production",  # type: ignore
#         ),
#     )

# Performance optimizations
TEMPLATES[0]["OPTIONS"]["debug"] = False  # noqa: F405
