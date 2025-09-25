# apps/orders/filters.py

from typing import ClassVar

import django_filters
from django.db import models

from apps.orders.models import Order


class OrderFilter(django_filters.FilterSet):
    """Filter set for orders with advanced filtering options."""

    # Date range filters
    date_from = django_filters.DateFilter(
        field_name="created_at__date",
        lookup_expr="gte",
        help_text="Filter orders from this date (YYYY-MM-DD)",
    )
    date_to = django_filters.DateFilter(
        field_name="created_at__date",
        lookup_expr="lte",
        help_text="Filter orders to this date (YYYY-MM-DD)",
    )

    # Amount range filters
    min_amount = django_filters.NumberFilter(
        field_name="total_amount",
        lookup_expr="gte",
        help_text="Minimum order amount",
    )
    max_amount = django_filters.NumberFilter(
        field_name="total_amount",
        lookup_expr="lte",
        help_text="Maximum order amount",
    )

    # Status filters
    status = django_filters.ChoiceFilter(
        choices=Order.OrderStatus.choices,
        help_text="Filter by order status",
    )
    payment_status = django_filters.ChoiceFilter(
        choices=Order.PaymentStatus.choices,
        help_text="Filter by payment status",
    )

    # Location filters
    shipping_country = django_filters.CharFilter(
        field_name="shipping_country",
        lookup_expr="icontains",
        help_text="Filter by shipping country",
    )
    shipping_state = django_filters.CharFilter(
        field_name="shipping_state",
        lookup_expr="icontains",
        help_text="Filter by shipping state",
    )

    # Boolean filters
    has_tracking = django_filters.BooleanFilter(
        method="filter_has_tracking",
        help_text="Filter orders that have tracking numbers",
    )
    is_shipped = django_filters.BooleanFilter(
        method="filter_is_shipped",
        help_text="Filter orders that have been shipped",
    )
    is_delivered = django_filters.BooleanFilter(
        method="filter_is_delivered",
        help_text="Filter orders that have been delivered",
    )

    class Meta:
        model = Order
        fields: ClassVar[list] = [
            "status",
            "payment_status",
            "shipping_country",
            "shipping_state",
            "user",
        ]

    def filter_has_tracking(self, queryset, name, value):
        """Filter orders that have tracking numbers."""
        if value:
            return queryset.exclude(
                models.Q(tracking_number="") | models.Q(tracking_number__isnull=True),
            )
        return queryset.filter(
            models.Q(tracking_number="") | models.Q(tracking_number__isnull=True),
        )

    def filter_is_shipped(self, queryset, name, value):
        """Filter orders by shipped status."""
        if value:
            return queryset.filter(shipped_at__isnull=False)
        return queryset.filter(shipped_at__isnull=True)

    def filter_is_delivered(self, queryset, name, value):
        """Filter orders by delivered status."""
        if value:
            return queryset.filter(delivered_at__isnull=False)
        return queryset.filter(delivered_at__isnull=True)
