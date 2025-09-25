# apps/orders/utils.py

from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.db import transaction

from apps.orders.models import Order
from apps.products.models import Product


class OrderCalculator:
    """Utility class for order calculations."""

    @staticmethod
    def calculate_tax(subtotal: Decimal, tax_rate: Decimal | None = None) -> Decimal:
        """Calculate tax amount based on subtotal."""
        if tax_rate is None:
            tax_rate = getattr(settings, "DEFAULT_TAX_RATE", Decimal("0.10"))

        return subtotal * tax_rate

    @staticmethod
    def calculate_shipping(
        total_weight: Decimal | None,
        shipping_method: str = "standard",
    ) -> Decimal:
        """Calculate shipping cost based on weight and method."""
        # Simple shipping calculation - you can make this more sophisticated
        shipping_rates = {
            "standard": Decimal("5.99"),
            "express": Decimal("12.99"),
            "overnight": Decimal("24.99"),
            "free": Decimal("0.00"),
        }

        base_rate = shipping_rates.get(shipping_method, shipping_rates["standard"])

        # Free shipping over $50
        if base_rate > 0 and hasattr(settings, "FREE_SHIPPING_THRESHOLD"):
            getattr(settings, "FREE_SHIPPING_THRESHOLD", Decimal("50.00"))
            # Note: This would need the subtotal passed in for a real implementation
            # For now, we'll return the base rate

        return base_rate

    @staticmethod
    def calculate_discount(subtotal: Decimal, discount_code: str | None) -> Decimal:
        """Calculate discount amount based on discount code."""
        # Placeholder for discount logic
        # You would implement your actual discount/coupon logic here
        return Decimal("0.00")

    @classmethod
    def calculate_order_totals(
        cls,
        subtotal: Decimal,
        shipping_method: str = "standard",
        discount_code: str | None = None,
        tax_rate: Decimal | None = None,
    ) -> dict[str, Decimal]:
        """Calculate all order totals."""

        tax_amount = cls.calculate_tax(subtotal, tax_rate)
        shipping_cost = cls.calculate_shipping(shipping_method=shipping_method)
        discount_amount = cls.calculate_discount(subtotal, discount_code)

        total = subtotal + tax_amount + shipping_cost - discount_amount

        return {
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "shipping_cost": shipping_cost,
            "discount_amount": discount_amount,
            "total": total,
        }


class InventoryManager:
    """Utility class for inventory management."""

    @staticmethod
    def check_availability(items: list[dict]) -> list[dict]:
        """Check inventory availability for list of items."""

        availability_results = []

        for item in items:
            product_id = item.get("product_id")
            requested_quantity = item.get("quantity", 1)

            try:
                product = Product.objects.get(id=product_id, is_active=True)
                is_available = product.stock_quantity >= requested_quantity

                availability_results.append(
                    {
                        "product_id": product_id,
                        "product_name": product.name,
                        "requested_quantity": requested_quantity,
                        "available_quantity": product.stock_quantity,
                        "is_available": is_available,
                    },
                )

            except Product.DoesNotExist:
                availability_results.append(
                    {
                        "product_id": product_id,
                        "product_name": "Unknown",
                        "requested_quantity": requested_quantity,
                        "available_quantity": 0,
                        "is_available": False,
                    },
                )

        return availability_results

    @staticmethod
    def reserve_inventory(items: list[dict]) -> bool:
        """Reserve inventory for order items."""

        try:
            with transaction.atomic():
                for item in items:
                    product = Product.objects.select_for_update().get(
                        id=item["product_id"],
                    )

                    if product.stock_quantity < item["quantity"]:
                        err_msg = f"Insufficient stock for {product.name}"
                        raise ValueError(err_msg)

                    product.stock_quantity -= item["quantity"]
                    product.save(update_fields=["stock_quantity", "updated_at"])

                return True

        except Exception:
            return False

    @staticmethod
    def release_inventory(items: list[dict]) -> bool:
        """Release reserved inventory (e.g., when order is cancelled)."""

        try:
            with transaction.atomic():
                for item in items:
                    product = Product.objects.select_for_update().get(
                        id=item["product_id"],
                    )

                    product.stock_quantity += item["quantity"]
                    product.save(update_fields=["stock_quantity", "updated_at"])

                return True

        except Exception:
            return False


class OrderStatusManager:
    """Utility class for managing order status transitions."""

    # Define allowed status transitions
    ALLOWED_TRANSITIONS: ClassVar = {
        Order.OrderStatus.PENDING: [
            Order.OrderStatus.CONFIRMED,
            Order.OrderStatus.CANCELLED,
        ],
        Order.OrderStatus.CONFIRMED: [
            Order.OrderStatus.PROCESSING,
            Order.OrderStatus.CANCELLED,
        ],
        Order.OrderStatus.PROCESSING: [
            Order.OrderStatus.SHIPPED,
            Order.OrderStatus.CANCELLED,
        ],
        Order.OrderStatus.SHIPPED: [
            Order.OrderStatus.DELIVERED,
            Order.OrderStatus.RETURNED,
        ],
        Order.OrderStatus.DELIVERED: [
            Order.OrderStatus.RETURNED,
            Order.OrderStatus.REFUNDED,
        ],
        Order.OrderStatus.CANCELLED: [],  # Terminal state
        Order.OrderStatus.RETURNED: [
            Order.OrderStatus.REFUNDED,
        ],
        Order.OrderStatus.REFUNDED: [],  # Terminal state
    }

    @classmethod
    def can_transition(cls, current_status: str, new_status: str) -> bool:
        """Check if status transition is allowed."""
        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, [])
        return new_status in allowed

    @classmethod
    def get_allowed_transitions(cls, current_status: str) -> list[str]:
        """Get list of allowed status transitions from current status."""
        return cls.ALLOWED_TRANSITIONS.get(current_status, [])
