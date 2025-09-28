# apps/orders/signals.py

import structlog
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.template.loader import render_to_string

from apps.orders.enums import OrderStatus
from apps.orders.models import Order, OrderItem

logger = structlog.get_logger(__name__)


@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, created, **kwargs):
    """Handle order status changes and send appropriate notifications."""

    if created:
        # Send order confirmation email
        send_order_confirmation_email(instance)

    elif hasattr(instance, "_state") and instance.state.fields_cache.get("status"):
        # Status has changed
        old_status = instance._state.fields_cache["status"]
        new_status = instance.status

        if old_status != new_status:
            # Send status change notification
            send_order_status_change_email(instance, old_status, new_status)


def send_order_confirmation_email(order):
    """Send order confirmation email to customer."""
    try:
        subject = f"Order Confirmation - {order.order_number}"

        context = {
            "order": order,
            "site_name": getattr(settings, "SITE_NAME", "E-Commerce Store"),
            "frontend_url": getattr(settings, "FRONTEND_URL", ""),
        }

        html_message = render_to_string("emails/order_confirmation.html", context)
        plain_message = render_to_string("emails/order_confirmation.txt", context)

        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=True,
        )

    except Exception as e:
        # Log error but don't raise exception

        logger.error(f"Failed to send order confirmation email: {e}")


def send_order_status_change_email(order, old_status, new_status):
    """Send email notification when order status changes."""
    try:
        # Only send emails for significant status changes
        notify_statuses = [
            OrderStatus.CONFIRMED,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
        ]

        if new_status not in notify_statuses:
            return

        subject_mapping = {
            OrderStatus.CONFIRMED: f"Order Confirmed - {order.order_number}",
            OrderStatus.SHIPPED: f"Order Shipped - {order.order_number}",
            OrderStatus.DELIVERED: f"Order Delivered - {order.order_number}",
            OrderStatus.CANCELLED: f"Order Cancelled - {order.order_number}",
        }

        subject = subject_mapping.get(
            new_status,
            f"Order Update - {order.order_number}",
        )

        context = {
            "order": order,
            "old_status": old_status,
            "new_status": new_status,
            "site_name": getattr(settings, "SITE_NAME", "E-Commerce Store"),
            "frontend_url": getattr(settings, "FRONTEND_URL", ""),
        }

        html_message = render_to_string("emails/order_status_change.html", context)
        plain_message = render_to_string("emails/order_status_change.txt", context)

        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=True,
        )

    except Exception as e:
        # Log error but don't raise exception

        logger.error(f"Failed to send order status change email: {e}")


@receiver(pre_delete, sender=OrderItem)
def handle_order_item_deletion(sender, instance, **kwargs):
    """Handle order item deletion by restoring stock if order is not confirmed."""
    # Only restore stock for pending/cancelled orders with a valid product
    if (
        instance.order.status
        in [
            OrderStatus.PENDING,
            OrderStatus.CANCELLED,
        ]
        and instance.product
    ):
        instance.product.stock_quantity += instance.quantity
        instance.product.save(update_fields=["stock_quantity", "updated_at"])
