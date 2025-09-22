# ecommerce_backend/settings/development.py

from .base import *  # noqa: F403

DEBUG = True


# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ENVIRONMENT = (env("ENVIRONMENT", default="development"),)  # noqa: F405 # type: ignore
