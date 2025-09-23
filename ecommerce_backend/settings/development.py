# ecommerce_backend/settings/development.py

from .base import *  # noqa: F403

DEBUG = True

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ENVIRONMENT = (env("ENVIRONMENT", default="development"),)  # noqa: F405 # type: ignore

# Session settings
CSRF_USE_SESSIONS = False  # Use cookie-based CSRF
CSRF_COOKIE_SECURE = False  # Allow HTTP in development
SESSION_COOKIE_SECURE = False
