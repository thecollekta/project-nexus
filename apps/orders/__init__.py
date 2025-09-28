# apps/orders/__init__.py

"""
Orders app for managing shopping carts and order processing.
"""

from apps.orders.enums import OrderStatus, PaymentStatus

__all__ = [
    "OrderStatus",
    "PaymentStatus",
]
