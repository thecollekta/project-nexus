# ecommerce_backend/settings/development.py

from .base import *  # noqa: F403

# Core settings
DEBUG = True
ENVIRONMENT = env("ENVIRONMENT", default="development")  # noqa: F405 # type: ignore

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Database - ensure it uses local PostgreSQL without SSL
DATABASES["default"]["OPTIONS"]["sslmode"] = "disable"  # noqa: F405

# Session settings for development
CSRF_USE_SESSIONS = False  # Use cookie-based CSRF
CSRF_COOKIE_SECURE = False  # Allow HTTP in development
SESSION_COOKIE_SECURE = False

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Enable browsable API
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += [  # noqa: F405
    "rest_framework.renderers.BrowsableAPIRenderer",
]

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE += [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware"
]  # For API requests

# Celery settings for development
CELERY_TASK_ALWAYS_EAGER = env.bool(
    "CELERY_TASK_ALWAYS_EAGER", default=False
)  # noqa: F405
CELERY_TASK_EAGER_PROPAGATES = True

# Cache settings for development (more permissive timeouts)
CACHES["default"]["OPTIONS"].update(  # noqa: F405
    {
        "SOCKET_CONNECT_TIMEOUT": 10,
        "SOCKET_TIMEOUT": 10,
    }
)
