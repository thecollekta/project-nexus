# apps/orders/apps.py

from contextlib import suppress

from django.apps import AppConfig


class OrdersConfig(AppConfig):
    """Configuration for the orders app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    label = "orders"
    verbose_name = "Orders"

    def ready(self):
        """Import signals when app is ready."""
        with suppress(ImportError):
            import apps.orders.signals  # noqa
