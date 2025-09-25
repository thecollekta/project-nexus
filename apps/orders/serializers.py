# apps/orders/serializers.py

"""
Serializers for the order management system.
Handles cart operations, order creation, and order lifecycle management.
"""

from decimal import Decimal
from typing import Any, ClassVar

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.core.serializers import BaseModelSerializer, SanitizedCharField
from apps.orders.models import Cart, CartItem, Order, OrderItem
from apps.products.models import Product
from apps.products.serializers import ProductListSerializer

User = get_user_model()


class CartItemSerializer(BaseModelSerializer):
    """
    Serializer for cart items with product details.
    """

    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta(BaseModelSerializer.Meta):
        model = CartItem
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "product",
            "product_id",
            "quantity",
            "price",
            "total_price",
        ]
        read_only_fields: ClassVar[ClassVar] = [
            *BaseModelSerializer.Meta.read_only_fields,
            "price",
        ]

    def validate_product_id(self, value: str) -> Product:
        """Validate product exists and is available."""
        try:
            product = Product.objects.get(id=value, is_active=True)
        except Product.DoesNotExist as exc:
            err_msg = "Product not found or unavailable"
            raise serializers.ValidationError(err_msg) from exc

        if product.stock_quantity <= 0:
            err_msg = "Product is out of stock"
            raise serializers.ValidationError(err_msg)

        return product

    def validate_quantity(self, value: int) -> int:
        """Validate quantity is positive and within stock limits."""
        if value <= 0:
            err_msg = "Quantity must be greater than 0"
            raise serializers.ValidationError(err_msg)

        # Additional validation will be done at the product level
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation for stock availability."""
        if "product_id" in attrs and "quantity" in attrs:
            try:
                product = Product.objects.get(id=attrs["product_id"])
                if product.stock_quantity < attrs["quantity"]:
                    raise serializers.ValidationError(
                        {
                            "quantity": f"Only {product.stock_quantity} items available in stock",
                        },
                    )
            except Product.DoesNotExist:
                pass  # This will be caught by product_id validation

        return attrs

    def create(self, validated_data: dict[str, Any]) -> CartItem:
        """Create cart item with proper product association."""
        product_id = validated_data.pop("product_id")
        product = Product.objects.get(id=product_id)

        validated_data["product"] = product
        validated_data["price"] = product.price

        return super().create(validated_data)

    def to_representation(self, instance: CartItem) -> dict[str, Any]:
        """Add calculated total price to representation."""
        representation = super().to_representation(instance)
        representation["total_price"] = instance.get_total_price()
        return representation


class CartSerializer(BaseModelSerializer):
    """
    Serializer for shopping cart with items and totals.
    """

    items = CartItemSerializer(many=True, read_only=True)
    totals = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Cart
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "user",
            "session_key",
            "expires_at",
            "total_amount",
            "item_count",
            "items",
            "totals",
            "is_expired",
        ]
        read_only_fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.read_only_fields,
            "total_amount",
            "item_count",
            "expires_at",
        ]

    def get_totals(self, obj: Cart) -> dict[str, Any]:
        """Calculate and return detailed cart totals."""
        return obj.calculate_totals()

    def get_is_expired(self, obj: Cart) -> bool:
        """Check if cart is expired."""
        return obj.is_expired()


class AddToCartSerializer(serializers.Serializer):
    """
    Serializer for adding items to cart.
    """

    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value: str) -> str:
        """Validate product exists and is available."""
        try:
            product = Product.objects.get(id=value, is_active=True)
        except Product.DoesNotExist as exc:
            err_msg = "Product not found or unavailable"
            raise serializers.ValidationError(err_msg) from exc

        if product.stock_quantity <= 0:
            err_msg = "Product is out of stock"
            raise serializers.ValidationError(err_msg)

        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate stock availability for requested quantity."""
        try:
            product = Product.objects.get(id=attrs["product_id"])
            if product.stock_quantity < attrs["quantity"]:
                raise serializers.ValidationError(
                    {
                        "quantity": f"Only {product.stock_quantity} items available in stock",
                    },
                )
        except Product.DoesNotExist:
            pass  # Will be caught by product_id validation

        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    """
    Serializer for updating cart item quantities.
    """

    quantity = serializers.IntegerField(min_value=0)

    def validate_quantity(self, value: int) -> int:
        """Validate quantity against stock availability."""
        if hasattr(self, "instance") and self.instance:
            product = self.instance.product
            if value > product.stock_quantity:
                err_msg = f"Only {product.stock_quantity} items available in stock"
                raise serializers.ValidationError(err_msg)
        return value


class OrderItemSerializer(BaseModelSerializer):
    """
    Serializer for order items with historical product information.
    """

    product = ProductListSerializer(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = OrderItem
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "price",
            "total_price",
        ]
        read_only_fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.read_only_fields,
            "product_name",
            "product_sku",
            "total_price",
        ]


class OrderSerializer(BaseModelSerializer):
    """
    Comprehensive serializer for orders with full details.
    """

    items = OrderItemSerializer(many=True, read_only=True)
    user_details = serializers.SerializerMethodField()
    shipping_address = serializers.SerializerMethodField()
    billing_address = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_status_display = serializers.CharField(
        source="get_payment_status_display",
        read_only=True,
    )
    can_cancel = serializers.SerializerMethodField()
    can_ship = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Order
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "order_number",
            "user",
            "user_details",
            "email",
            "phone_number",
            "shipping_first_name",
            "shipping_last_name",
            "shipping_address_line_1",
            "shipping_address_line_2",
            "shipping_city",
            "shipping_state",
            "shipping_postal_code",
            "shipping_country",
            "billing_same_as_shipping",
            "billing_first_name",
            "billing_last_name",
            "billing_address_line_1",
            "billing_address_line_2",
            "billing_city",
            "billing_state",
            "billing_postal_code",
            "billing_country",
            "status",
            "status_display",
            "payment_status",
            "payment_status_display",
            "subtotal",
            "tax_amount",
            "shipping_cost",
            "discount_amount",
            "total_amount",
            "tracking_number",
            "carrier",
            "estimated_delivery_date",
            "shipped_at",
            "delivered_at",
            "notes",
            "customer_notes",
            "items",
            "shipping_address",
            "billing_address",
            "can_cancel",
            "can_ship",
        ]
        read_only_fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.read_only_fields,
            "order_number",
            "subtotal",
            "total_amount",
            "shipped_at",
            "delivered_at",
        ]

    def get_user_details(self, obj: Order) -> dict[str, Any]:
        """Return user details for the order."""
        return {
            "id": str(obj.user.id),
            "username": obj.user.username,
            "email": obj.user.email,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
        }

    def get_shipping_address(self, obj: Order) -> str:
        """Return formatted shipping address."""
        return obj.get_full_shipping_address()

    def get_billing_address(self, obj: Order) -> str:
        """Return formatted billing address."""
        return obj.get_full_billing_address()

    def get_can_cancel(self, obj: Order) -> bool:
        """Check if order can be cancelled."""
        return obj.can_be_cancelled()

    def get_can_ship(self, obj: Order) -> bool:
        """Check if order can be shipped."""
        return obj.can_be_shipped()


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating orders from cart items.
    """

    # Contact information
    email = serializers.EmailField()
    phone_number = SanitizedCharField(max_length=20)

    # Shipping address
    shipping_first_name = SanitizedCharField(max_length=50)
    shipping_last_name = SanitizedCharField(max_length=50)
    shipping_address_line_1 = SanitizedCharField(max_length=255)
    shipping_address_line_2 = SanitizedCharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    shipping_city = SanitizedCharField(max_length=100)
    shipping_state = SanitizedCharField(max_length=100)
    shipping_postal_code = SanitizedCharField(max_length=20)
    shipping_country = SanitizedCharField(max_length=100, default="United States")

    # Billing address
    billing_same_as_shipping = serializers.BooleanField(default=True)
    billing_first_name = SanitizedCharField(
        max_length=50,
        required=False,
        allow_blank=True,
    )
    billing_last_name = SanitizedCharField(
        max_length=50,
        required=False,
        allow_blank=True,
    )
    billing_address_line_1 = SanitizedCharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    billing_address_line_2 = SanitizedCharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    billing_city = SanitizedCharField(max_length=100, required=False, allow_blank=True)
    billing_state = SanitizedCharField(max_length=100, required=False, allow_blank=True)
    billing_postal_code = SanitizedCharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )
    billing_country = SanitizedCharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    # Order notes
    customer_notes = SanitizedCharField(
        required=False,
        allow_blank=True,
        style={"base_template": "textarea.html"},
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate billing address if not same as shipping."""
        if not attrs.get("billing_same_as_shipping", True):
            billing_fields = [
                "billing_first_name",
                "billing_last_name",
                "billing_address_line_1",
                "billing_city",
                "billing_state",
                "billing_postal_code",
                "billing_country",
            ]

            missing_fields = []
            for field in billing_fields:
                if not attrs.get(field):
                    missing_fields.append(
                        field.replace("billing_", "").replace("_", " ").title(),
                    )

            if missing_fields:
                raise serializers.ValidationError(
                    {
                        "billing_address": f"Required billing fields: {', '.join(missing_fields)}",
                    },
                )

        return attrs

    @transaction.atomic
    def create_order_from_cart(self, user: User, cart: Cart) -> Order:
        """Create order from cart contents."""
        if not cart.items.exists():
            err_msg = "Cart is empty"
            raise serializers.ValidationError(err_msg)

        # Validate all cart items have sufficient stock
        insufficient_stock = []
        for item in cart.items.select_related("product"):
            if item.product.stock_quantity < item.quantity:
                insufficient_stock.append(
                    {
                        "product": item.product.name,
                        "requested": item.quantity,
                        "available": item.product.stock_quantity,
                    },
                )

        if insufficient_stock:
            raise serializers.ValidationError(
                {
                    "stock_errors": insufficient_stock,
                },
            )

        # Calculate totals
        totals = cart.calculate_totals()

        # Create order
        order_data = {
            "user": user,
            "subtotal": totals["subtotal"],
            "tax_amount": totals["tax_amount"],
            "total_amount": totals["total"],
            "shipping_cost": Decimal("0.00"),  # You can implement shipping calculation
            "discount_amount": Decimal("0.00"),  # You can implement discount logic
        }

        # Add validated data to order
        order_data.update(self.validated_data)

        # Copy billing address from shipping if same
        if order_data.get("billing_same_as_shipping", True):
            order_data.update(
                {
                    "billing_first_name": order_data["shipping_first_name"],
                    "billing_last_name": order_data["shipping_last_name"],
                    "billing_address_line_1": order_data["shipping_address_line_1"],
                    "billing_address_line_2": order_data.get(
                        "shipping_address_line_2",
                        "",
                    ),
                    "billing_city": order_data["shipping_city"],
                    "billing_state": order_data["shipping_state"],
                    "billing_postal_code": order_data["shipping_postal_code"],
                    "billing_country": order_data["shipping_country"],
                },
            )

        # Create the order
        order = Order.objects.create(**order_data)

        # Create order items from cart items
        for cart_item in cart.items.select_related("product"):
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.price,
            )

            # Reduce product stock
            cart_item.product.stock_quantity -= cart_item.quantity
            cart_item.product.save(update_fields=["stock_quantity", "updated_at"])

        # Clear the cart
        cart.clear()

        return order


class OrderUpdateSerializer(BaseModelSerializer):
    """
    Serializer for updating order details (admin use).
    """

    class Meta(BaseModelSerializer.Meta):
        model = Order
        fields: ClassVar[list] = [
            "status",
            "payment_status",
            "tracking_number",
            "carrier",
            "estimated_delivery_date",
            "notes",
        ]

    def validate_status(self, value: str) -> str:
        """Validate status transitions."""
        if self.instance:
            current_status = self.instance.status

            # Define allowed status transitions
            allowed_transitions = {
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

            if value != current_status and value not in allowed_transitions.get(
                current_status,
                [],
            ):
                err_msg = f"Cannot change status from {current_status} to {value}"
                raise serializers.ValidationError(err_msg)

        return value


class OrderShipmentSerializer(serializers.Serializer):
    """
    Serializer for shipping orders.
    """

    tracking_number = SanitizedCharField(max_length=100)
    carrier = SanitizedCharField(max_length=100)
    estimated_delivery_date = serializers.DateField(required=False)

    def ship_order(self, order: Order) -> Order:
        """Ship the order with provided tracking information."""
        if not order.can_be_shipped():
            err_msg = "Order cannot be shipped in current state"
            raise serializers.ValidationError(err_msg)

        order.mark_as_shipped(
            tracking_number=self.validated_data["tracking_number"],
            carrier=self.validated_data["carrier"],
        )

        if "estimated_delivery_date" in self.validated_data:
            order.estimated_delivery_date = self.validated_data[
                "estimated_delivery_date"
            ]
            order.save(update_fields=["estimated_delivery_date", "updated_at"])

        return order


class OrderCancelSerializer(serializers.Serializer):
    """
    Serializer for cancelling orders.
    """

    reason = SanitizedCharField(required=False, allow_blank=True)

    def cancel_order(self, order: Order) -> Order:
        """Cancel the order with optional reason."""
        if not order.can_be_cancelled():
            err_msg = "Order cannot be cancelled in current state"
            raise serializers.ValidationError(err_msg)

        order.cancel(reason=self.validated_data.get("reason", ""))
        return order


class OrderSummarySerializer(BaseModelSerializer):
    """
    Lightweight serializer for order lists and summaries.
    """

    user_name = serializers.CharField(source="user.username", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_status_display = serializers.CharField(
        source="get_payment_status_display",
        read_only=True,
    )
    item_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Order
        fields: ClassVar[list] = [
            "id",
            "order_number",
            "user_name",
            "status",
            "status_display",
            "payment_status",
            "payment_status_display",
            "total_amount",
            "item_count",
            "created_at",
            "shipped_at",
            "delivered_at",
        ]

    def get_item_count(self, obj: Order) -> int:
        """Get total number of items in the order."""
        return obj.items.count()


class OrderTrackingSerializer(serializers.ModelSerializer):
    """
    Serializer for order tracking information (public view).
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    shipping_address = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields: ClassVar[list] = [
            "order_number",
            "status",
            "status_display",
            "tracking_number",
            "carrier",
            "estimated_delivery_date",
            "shipped_at",
            "delivered_at",
            "shipping_address",
        ]

    def get_shipping_address(self, obj: Order) -> dict[str, str]:
        """Return shipping address components."""
        return {
            "name": f"{obj.shipping_first_name} {obj.shipping_last_name}",
            "city": obj.shipping_city,
            "state": obj.shipping_state,
            "country": obj.shipping_country,
        }


# Utility serializers for cart management
class CartTotalsSerializer(serializers.Serializer):
    """
    Serializer for cart totals calculation.
    """

    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    tax_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)


class ProductAvailabilitySerializer(serializers.Serializer):
    """
    Serializer for checking product availability in cart.
    """

    product_id = serializers.UUIDField()
    product_name = serializers.CharField(read_only=True)
    requested_quantity = serializers.IntegerField(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
