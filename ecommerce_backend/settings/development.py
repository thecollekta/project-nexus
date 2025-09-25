# ecommerce_backend/settings/development.py

from .base import *  # noqa: F403

DEBUG = True

ENVIRONMENT = (env("ENVIRONMENT", default="development"),)  # noqa: F405 # type: ignore

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Database - ensure it uses local PostgreSQL without SSL
DATABASES["default"]["OPTIONS"]["sslmode"] = "disable"  # Force disable SSL  # noqa: F405

# Session settings
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
