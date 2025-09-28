# apps/orders/enums.py

"""
Enums for the orders app.
"""

from django.db import models


class OrderStatus(models.TextChoices):
    """Order status choices."""

    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"
    RETURNED = "returned", "Returned"
    ON_HOLD = "on_hold", "On Hold"
    COMPLETED = "completed", "Completed"


class PaymentStatus(models.TextChoices):
    """Payment status choices."""

    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"
    VOIDED = "voided", "Voided"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
