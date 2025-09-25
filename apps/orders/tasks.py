# apps/orders/tasks.py

import csv
import io
from datetime import timedelta

import structlog
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from apps.orders.models import Cart, Order

User = get_user_model()

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email_task(self, order_id):
    """Send order confirmation email asynchronously."""
    try:
        order = (
            Order.objects.select_related("user")
            .prefetch_related("items__product")
            .get(id=order_id)
        )

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
            fail_silently=False,
        )

        logger.info(f"Order confirmation email sent for order {order.order_number}")

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for email confirmation")
    except Exception as exc:
        logger.error(f"Failed to send order confirmation email: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_shipping_notification_task(self, order_id):
    """Send shipping notification email asynchronously."""
    try:
        order = Order.objects.select_related("user").get(id=order_id)

        subject = f"Your Order Has Shipped - {order.order_number}"

        context = {
            "order": order,
            "site_name": getattr(settings, "SITE_NAME", "E-Commerce Store"),
            "frontend_url": getattr(settings, "FRONTEND_URL", ""),
        }

        html_message = render_to_string("emails/shipping_notification.html", context)
        plain_message = render_to_string("emails/shipping_notification.txt", context)

        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=False,
        )

        logger.info(f"Shipping notification sent for order {order.order_number}")

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for shipping notification")
    except Exception as exc:
        logger.error(f"Failed to send shipping notification: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task
def cleanup_expired_carts():
    """Clean up expired guest carts."""

    try:
        count = Cart.objects.cleanup_expired()
        logger.info(f"Cleaned up {count} expired carts")
        return count
    except Exception as exc:
        logger.error(f"Failed to cleanup expired carts: {exc}")
        raise


@shared_task
def update_order_statuses():
    """Update order statuses based on business rules."""

    try:
        updated_count = 0

        # Auto-confirm paid orders after 1 hour
        cutoff_time = timezone.now() - timedelta(hours=1)
        pending_paid_orders = Order.objects.filter(
            status=Order.OrderStatus.PENDING,
            payment_status=Order.PaymentStatus.PAID,
            created_at__lte=cutoff_time,
        )

        for order in pending_paid_orders:
            order.status = Order.OrderStatus.CONFIRMED
            order.save(update_fields=["status", "updated_at"])
            updated_count += 1

        # Auto-cancel unpaid orders after 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)
        old_pending_orders = Order.objects.filter(
            status=Order.OrderStatus.PENDING,
            payment_status=Order.PaymentStatus.PENDING,
            created_at__lte=cutoff_time,
        )

        for order in old_pending_orders:
            order.cancel("Automatically cancelled due to non-payment")
            updated_count += 1

        logger.info(f"Updated {updated_count} order statuses")
        return updated_count

    except Exception as exc:
        logger.error(f"Failed to update order statuses: {exc}")
        raise


@shared_task
def generate_order_report(start_date, end_date, user_id=None):
    """Generate order report for a date range."""

    try:
        # Build queryset
        orders = (
            Order.objects.filter(
                created_at__date__range=[start_date, end_date],
            )
            .select_related("user")
            .prefetch_related("items__product")
        )

        # Create CSV report
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Order Number",
                "Customer",
                "Email",
                "Status",
                "Payment Status",
                "Total Amount",
                "Items Count",
                "Order Date",
                "Shipped Date",
                "Delivered Date",
            ],
        )

        # Write data
        for order in orders:
            writer.writerow(
                [
                    order.order_number,
                    f"{order.user.first_name} {order.user.last_name}".strip()
                    or order.user.username,
                    order.email,
                    order.get_status_display(),
                    order.get_payment_status_display(),
                    str(order.total_amount),
                    order.items.count(),
                    order.created_at.strftime("%Y-%m-%d %H:%M"),
                    (
                        order.shipped_at.strftime("%Y-%m-%d %H:%M")
                        if order.shipped_at
                        else ""
                    ),
                    (
                        order.delivered_at.strftime("%Y-%m-%d %H:%M")
                        if order.delivered_at
                        else ""
                    ),
                ],
            )

        # Send report via email if user_id provided
        if user_id:
            try:
                user = User.objects.get(id=user_id)

                subject = f"Order Report ({start_date} to {end_date})"
                body = f"Please find attached the order report for {start_date} to {end_date}."

                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )

                email.attach(
                    f"order_report_{start_date}_to_{end_date}.csv",
                    output.getvalue(),
                    "text/csv",
                )

                email.send()
                logger.info(f"Order report sent to {user.email}")

            except User.DoesNotExist:
                logger.error(f"User {user_id} not found for report email")

        return output.getvalue()

    except Exception as exc:
        logger.error(f"Failed to generate order report: {exc}")
        raise
