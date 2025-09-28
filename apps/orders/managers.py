# apps/orders/managers.py

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.orders.enums import OrderStatus, PaymentStatus


class CartManager(models.Manager):
    """Custom manager for Cart model."""

    def active(self):
        """Return only active (non-expired) carts."""
        return self.get_queryset().filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now()),
        )

    def expired(self):
        """Return only expired carts."""
        return self.get_queryset().filter(
            expires_at__isnull=False,
            expires_at__lte=timezone.now(),
        )

    def for_user(self, user):
        """Get or create cart for authenticated user."""
        if not user.is_authenticated:
            return None

        cart, _ = self.get_or_create(
            user=user,
            defaults={"expires_at": None},
        )
        return cart

    def for_session(self, session_key, create=True):
        """Get or create cart for session key."""
        if not session_key:
            return None

        if create:
            expires_at = timezone.now() + timedelta(days=30)  # 30 day expiry
            cart, _ = self.get_or_create(
                session_key=session_key,
                user__isnull=True,
                defaults={"expires_at": expires_at},
            )
        else:
            try:
                cart = self.get(session_key=session_key, user__isnull=True)
            except self.model.DoesNotExist:
                cart = None

        return cart

    def cleanup_expired(self):
        """Remove expired guest carts."""
        expired_carts = self.expired()
        count = expired_carts.count()
        expired_carts.delete()
        return count


class OrderManager(models.Manager):
    """Custom manager for Order model."""

    def for_user(self, user):
        """Get orders for a specific user."""

        return self.get_queryset().filter(user=user)

    def pending(self):
        """Get pending orders."""

        return self.get_queryset().filter(status=OrderStatus.PENDING)

    def confirmed(self):
        """Get confirmed orders."""

        return self.get_queryset().filter(status=OrderStatus.CONFIRMED)

    def processing(self):
        """Get processing orders."""

        return self.get_queryset().filter(status=OrderStatus.PROCESSING)

    def shipped(self):
        """Get shipped orders."""

        return self.get_queryset().filter(status=OrderStatus.SHIPPED)

    def delivered(self):
        """Get delivered orders."""

        return self.get_queryset().filter(status=OrderStatus.DELIVERED)

    def cancelled(self):
        """Get cancelled orders."""

        return self.get_queryset().filter(status=OrderStatus.CANCELLED)

    def paid(self):
        """Get paid orders."""

        return self.get_queryset().filter(payment_status=PaymentStatus.PAID)

    def unpaid(self):
        """Get unpaid orders."""

        return self.get_queryset().filter(payment_status=PaymentStatus.PENDING)

    def recent(self, days=30):
        """Get orders from the last N days."""
        cutoff = timezone.now() - timedelta(days=days)
        return self.get_queryset().filter(created_at__gte=cutoff)

    def by_status(self, status):
        """Get orders by status."""
        return self.get_queryset().filter(status=status)

    def needs_shipping(self):
        """Get orders that need to be shipped."""

        return self.get_queryset().filter(
            status__in=[OrderStatus.CONFIRMED, OrderStatus.PROCESSING],
            payment_status=PaymentStatus.PAID,
        )
