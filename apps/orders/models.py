# apps/orders/models.py

"""
Order management models for the e-commerce system.
Handles cart functionality, order creation, and order lifecycle management.
"""

import random
import string
from contextlib import suppress
from decimal import Decimal
from typing import ClassVar

import structlog
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from djmoney.models.fields import MoneyField
from djmoney.money import Money

from apps.core.models import AuditStampedModelBase
from apps.core.utils import clean_price_value
from apps.orders.enums import OrderStatus, PaymentStatus
from apps.orders.managers import CartManager, OrderManager

logger = structlog.get_logger(__name__)


class Cart(AuditStampedModelBase):
    """
    Shopping cart model for temporary item storage.
    Allows guests and authenticated users to maintain cart state.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart",
        help_text="User who owns this cart (null for guest carts)",
    )

    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text="Session key for guest carts",
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this cart expires (for guest carts)",
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total amount of items in cart",
    )

    item_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of items in cart",
    )

    # Custom managers
    objects = CartManager()

    class Meta:
        db_table = "orders_cart"
        indexes: ClassVar[list] = [
            models.Index(fields=["user"]),
            models.Index(fields=["session_key"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["created_at"]),
        ]
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False)
                | models.Q(session_key__isnull=False),
                name="cart_must_have_user_or_session",
            ),
        ]

    def __str__(self) -> str:
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Guest cart {self.session_key}"

    def calculate_totals(self) -> dict:
        """Calculate and return cart totals."""
        items = self.items.select_related("product").all()

        subtotal = sum(item.get_total_price() for item in items)
        item_count = sum(item.quantity for item in items)

        # You can add tax calculation, shipping, discounts here
        tax_rate = Decimal("0.10")  # 10% tax
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount

        return {
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "total": total,
            "item_count": item_count,
        }

    def update_totals(self) -> None:
        """Update cached totals for performance."""
        totals = self.calculate_totals()
        self.total_amount = totals["total"]
        self.item_count = totals["item_count"]
        self.save(update_fields=["total_amount", "item_count", "updated_at"])

    def add_item(self, product, quantity: int) -> "CartItem":
        """
        Add item to cart with proper price handling

        Args:
            product: Product instance
            quantity: Item quantity
        """

        try:
            # Clean the product price
            price_decimal = clean_price_value(product.price)
            price_money = Money(price_decimal, "GHS")

            cart_item, created = self.items.get_or_create(
                product=product,
                defaults={"quantity": quantity, "price": price_money},
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            self.update_totals()
            return cart_item

        except Exception as e:
            logger.error(f"Failed to add item to cart: {str(e)}")
            raise

    def remove_item(self, product) -> None:
        """Remove item from cart."""
        self.items.filter(product=product).delete()
        self.update_totals()

    def clear(self) -> None:
        """Remove all items from cart."""
        self.items.all().delete()
        self.update_totals()

    def is_expired(self) -> bool:
        """Check if cart is expired (for guest carts)."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at


# apps/orders/models.py - CartItem class fixes


class CartItem(AuditStampedModelBase):
    """
    Individual items within a shopping cart.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Cart this item belongs to",
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="cart_items",
        help_text="Product in the cart",
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity of this product",
    )

    price = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency="GHS",
    )

    class Meta:
        db_table = "orders_cart_item"
        unique_together = ("cart", "product")
        indexes: ClassVar[list] = [
            models.Index(fields=["cart"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self) -> str:
        return f"{self.quantity}x {self.product.name} in {self.cart}"

    def get_total_price(self) -> Decimal:
        """Calculate total price for this cart item."""
        if isinstance(self.price, Money):
            return self.price.amount * self.quantity
        return self.price * self.quantity

    def clean(self) -> None:
        """Validate cart item data."""
        super().clean()

        # Check stock availability
        if self.product and self.quantity > self.product.stock_quantity:
            raise ValidationError(
                {
                    "quantity": f"Only {self.product.stock_quantity} items available in stock",
                },
            )

        # Clean and validate price before model validation
        if self.price is not None:
            try:
                # Handle various price formats
                if isinstance(self.price, str):
                    cleaned_price = clean_price_value(self.price)
                    self.price = Money(cleaned_price, "GHS")
                elif isinstance(self.price, (int, float)):
                    self.price = Money(Decimal(str(self.price)), "GHS")
                elif isinstance(self.price, Decimal):
                    self.price = Money(self.price, "GHS")
                elif hasattr(self.price, "amount") and not isinstance(
                    self.price, Money
                ):
                    # Handle case where it might be another money-like object
                    self.price = Money(self.price.amount, "GHS")

                # Ensure it's a Money object with correct currency
                if isinstance(self.price, Money) and self.price.currency != "GHS":
                    self.price = Money(self.price.amount, "GHS")

            except Exception as e:
                logger.error(f"Error cleaning price in CartItem: {str(e)}")
                raise ValidationError(f"Invalid price format: {self.price}")

    def save(self, *args, **kwargs):
        """Save cart item with proper price handling."""
        # Clean the price before validation
        self.full_clean()
        super().save(*args, **kwargs)


class Order(AuditStampedModelBase):
    """
    Order model representing a completed purchase.
    """

    # Order identification
    order_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique order number for customer reference",
    )

    # Customer information
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,  # Don't delete orders if user is deleted
        related_name="orders",
        help_text="Customer who placed the order",
    )

    # Contact information
    email = models.EmailField(
        help_text="Contact email for this order",
    )

    phone_number = models.CharField(
        max_length=20,
        help_text="Contact phone number",
    )

    # Shipping address
    shipping_first_name = models.CharField(
        max_length=50,
        help_text="Shipping address first name",
    )

    shipping_last_name = models.CharField(
        max_length=50,
        help_text="Shipping address last name",
    )

    shipping_address_line_1 = models.CharField(
        max_length=255,
        help_text="Shipping address line 1",
    )

    shipping_address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        help_text="Shipping address line 2",
    )

    shipping_city = models.CharField(
        max_length=100,
        help_text="Shipping city",
    )

    shipping_state = models.CharField(
        max_length=100,
        help_text="Shipping state/province",
    )

    shipping_postal_code = models.CharField(
        max_length=20,
        help_text="Shipping postal/ZIP code",
    )

    shipping_country = models.CharField(
        max_length=100,
        default="United States",
        help_text="Shipping country",
    )

    # Billing address (optional - can use shipping if same)
    billing_same_as_shipping = models.BooleanField(
        default=True,
        help_text="Whether billing address is same as shipping",
    )

    billing_first_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Billing address first name",
    )

    billing_last_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Billing address last name",
    )

    billing_address_line_1 = models.CharField(
        max_length=255,
        blank=True,
        help_text="Billing address line 1",
    )

    billing_address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        help_text="Billing address line 2",
    )

    billing_city = models.CharField(
        max_length=100,
        blank=True,
        help_text="Billing city",
    )

    billing_state = models.CharField(
        max_length=100,
        blank=True,
        help_text="Billing state/province",
    )

    billing_postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Billing postal/ZIP code",
    )

    billing_country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Billing country",
    )

    # Order details
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        help_text="Current order status",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text="Current payment status",
    )

    # Financial information
    subtotal = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency="GHS",
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("9999999.99")),
        ],
        help_text="Subtotal before tax and shipping",
    )

    tax_amount = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency="GHS",
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("9999999.99")),
        ],
        help_text="Tax amount",
    )

    shipping_cost = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency="GHS",
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("9999999.99")),
        ],
        help_text="Shipping cost",
    )

    discount_amount = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency="GHS",
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("9999999.99")),
        ],
        help_text="Total discount amount",
    )

    total_amount = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency="GHS",
        validators=[
            MinValueValidator(Decimal("0.01")),
            MaxValueValidator(Decimal("9999999.99")),
        ],
        help_text="Final total amount",
    )

    # Tracking and fulfillment
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Shipping tracking number",
    )

    carrier = models.CharField(
        max_length=100,
        blank=True,
        help_text="Shipping carrier (FedEx, UPS, etc.)",
    )

    estimated_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Estimated delivery date",
    )

    shipped_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the order was shipped",
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the order was delivered",
    )

    # Internal notes
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about the order",
    )

    customer_notes = models.TextField(
        blank=True,
        help_text="Customer-provided notes or special instructions",
    )

    # Custom managers
    objects = OrderManager()

    class Meta:
        db_table = "orders_order"
        ordering: ClassVar[list[str]] = ["-created_at"]
        indexes: ClassVar[list] = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["shipped_at"]),
            models.Index(fields=["delivered_at"]),
        ]

    def __str__(self) -> str:
        return f"Order {self.order_number} - {self.user.username}"

    def save(self, *args, **kwargs) -> None:
        """Generate order number if not exists."""
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self) -> str:
        """Generate unique order number."""

        while True:
            # Format: ORD-YYYYMMDD-XXXXX (ORD-20241215-AB123)  # noqa: ERA001
            date_str = timezone.now().strftime("%Y%m%d")
            random_str = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=5),
            )
            order_number = f"ORD-{date_str}-{random_str}"

            if not Order.objects.filter(order_number=order_number).exists():
                return order_number

    def get_full_shipping_address(self) -> str:
        """Return formatted shipping address."""
        address_parts = [
            f"{self.shipping_first_name} {self.shipping_last_name}",
            self.shipping_address_line_1,
        ]

        if self.shipping_address_line_2:
            address_parts.append(self.shipping_address_line_2)

        address_parts.extend(
            [
                f"{self.shipping_city}, {self.shipping_state} {self.shipping_postal_code}",
                self.shipping_country,
            ],
        )

        return "\n".join(address_parts)

    def get_full_billing_address(self) -> str:
        """Return formatted billing address."""
        if self.billing_same_as_shipping:
            return self.get_full_shipping_address()

        address_parts = [
            f"{self.billing_first_name} {self.billing_last_name}",
            self.billing_address_line_1,
        ]

        if self.billing_address_line_2:
            address_parts.append(self.billing_address_line_2)

        address_parts.extend(
            [
                f"{self.billing_city}, {self.billing_state} {self.billing_postal_code}",
                self.billing_country,
            ],
        )

        return "\n".join(address_parts)

    def calculate_total(self) -> Decimal:
        """Calculate order total from components."""
        return (
            self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
        )

    def can_be_cancelled(self) -> bool:
        """Check if order can be cancelled."""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]

    def can_be_shipped(self) -> bool:
        """Check if order can be shipped."""
        return (
            self.status in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]
            and self.payment_status == PaymentStatus.PAID
        )

    @transaction.atomic
    def mark_as_shipped(self, tracking_number: str = "", carrier: str = "") -> None:
        """Mark order as shipped and update tracking info."""
        if not self.can_be_shipped():
            err_msg = "Order cannot be shipped in current state"
            raise ValueError(err_msg)

        self.status = OrderStatus.SHIPPED
        self.shipped_at = timezone.now()

        if tracking_number:
            self.tracking_number = tracking_number
        if carrier:
            self.carrier = carrier

        self.save(
            update_fields=[
                "status",
                "shipped_at",
                "tracking_number",
                "carrier",
                "updated_at",
            ],
        )

    @transaction.atomic
    def mark_as_delivered(self) -> None:
        """Mark order as delivered."""
        if self.status != OrderStatus.SHIPPED:
            err_msg = "Order must be shipped before marking as delivered"
            raise ValueError(err_msg)

        self.status = OrderStatus.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=["status", "delivered_at", "updated_at"])

    @transaction.atomic
    def cancel(self, reason: str = "") -> None:
        """Cancel the order and restore inventory."""
        if not self.can_be_cancelled():
            err_msg = "Order cannot be cancelled in current state"
            raise ValueError(err_msg)

        # Restore inventory for all items
        for item in self.items.all():
            item.product.stock_quantity += item.quantity
            item.product.save(update_fields=["stock_quantity", "updated_at"])

        self.status = OrderStatus.CANCELLED
        if reason:
            self.notes = f"Cancelled: {reason}\n{self.notes}"
        self.save(update_fields=["status", "notes", "updated_at"])


class OrderItem(AuditStampedModelBase):
    """
    Individual items within an order.
    """

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Order this item belongs to",
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,  # Don't delete order items if product is deleted
        related_name="order_items",
        help_text="Product that was ordered",
    )

    # Product details at time of order (for historical accuracy)
    product_name = models.CharField(
        max_length=255,
        help_text="Product name at time of order",
    )

    product_sku = models.CharField(
        max_length=100,
        help_text="Product SKU at time of order",
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity ordered",
    )

    price = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency="GHS",
        validators=[
            MinValueValidator(Decimal("0.01")),
            MaxValueValidator(Decimal("9999999.99")),
        ],
        help_text="Price per unit at time of order",
    )

    total_price = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency="GHS",
        validators=[
            MinValueValidator(Decimal("0.01")),
            MaxValueValidator(Decimal("9999999.99")),
        ],
        help_text="Total price for this line item",
    )

    class Meta:
        db_table = "orders_order_item"
        indexes: ClassVar[list] = [
            models.Index(fields=["order"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self) -> str:
        return f"{self.quantity}x {self.product_name} (Order {self.order.order_number})"

    def save(self, *args, **kwargs) -> None:
        """Calculate total price and populate product details."""
        if self.product:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            if not self.price:
                self.price = self.product.price

        self.total_price = self.price * self.quantity
        super().save(*args, **kwargs)


# Signals for automatic cleanup
@receiver(post_save, sender=CartItem)
@receiver(post_delete, sender=CartItem)
def update_cart_totals(sender, instance, **kwargs):
    """Update cart totals when cart items change."""
    if instance.cart_id:
        with suppress(Cart.DoesNotExist):
            instance.cart.update_totals()


@receiver(post_save, sender=OrderItem)
def update_order_subtotal(sender, instance, **kwargs):
    """Update order subtotal when order items change."""
    if instance.order_id:
        order = instance.order
        subtotal = sum(item.total_price for item in order.items.all())

        if order.subtotal != subtotal:
            order.subtotal = subtotal
            order.total_amount = order.calculate_total()
            order.save(update_fields=["subtotal", "total_amount", "updated_at"])
