# apps/orders/admin.py

from typing import ClassVar

from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.orders.models import Cart, CartItem, Order, OrderItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin interface for Cart model."""

    list_display: ClassVar[list] = [
        "id",
        "user_display",
        "session_key",
        "item_count",
        "total_amount",
        "created_at",
        "is_expired_display",
    ]
    list_filter: ClassVar[list] = ["created_at", "updated_at"]
    search_fields: ClassVar[list] = ["user__username", "user__email", "session_key"]
    readonly_fields: ClassVar[list] = [
        "id",
        "created_at",
        "updated_at",
        "total_amount",
        "item_count",
    ]
    raw_id_fields: ClassVar[list] = ["user"]

    def user_display(self, obj):
        """Display user or session for cart."""
        if obj.user:
            return obj.user.username
        return f"Guest ({obj.session_key[:8]}...)"

    user_display.short_description = "User"

    def is_expired_display(self, obj):
        """Display if cart is expired."""
        if obj.is_expired():
            return format_html('<span style="color: red;">Expired</span>')
        return format_html('<span style="color: green;">Active</span>')

    is_expired_display.short_description = "Status"


class CartItemInline(admin.TabularInline):
    """Inline admin for cart items."""

    model = CartItem
    extra = 0
    readonly_fields: ClassVar[list] = ["created_at", "updated_at"]
    raw_id_fields: ClassVar[list] = ["product"]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Admin interface for CartItem model."""

    list_display: ClassVar[list] = [
        "id",
        "cart",
        "product",
        "quantity",
        "price",
        "total_price_display",
    ]
    list_filter: ClassVar[list] = ["created_at", "updated_at"]
    search_fields: ClassVar[list] = [
        "product__name",
        "product__sku",
        "cart__user__username",
    ]
    readonly_fields: ClassVar[list] = ["id", "created_at", "updated_at"]
    raw_id_fields: ClassVar[list] = ["cart", "product"]

    def total_price_display(self, obj):
        """Display calculated total price."""
        return f"¢{obj.get_total_price():.2f}"

    total_price_display.short_description = "Total Price"


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items."""

    model = OrderItem
    extra = 0
    readonly_fields: ClassVar[list] = [
        "id",
        "product_name",
        "product_sku",
        "total_price",
        "created_at",
    ]
    raw_id_fields: ClassVar[list] = ["product"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model."""

    list_display: ClassVar[list] = [
        "order_number",
        "user_link",
        "status_display",
        "payment_status_display",
        "total_amount",
        "created_at",
        "actions_display",
    ]
    list_filter: ClassVar[list] = [
        "status",
        "payment_status",
        "created_at",
        "shipped_at",
        "delivered_at",
    ]
    search_fields: ClassVar[list] = [
        "order_number",
        "user__username",
        "user__email",
        "email",
        "shipping_first_name",
        "shipping_last_name",
    ]
    readonly_fields: ClassVar[list] = [
        "id",
        "order_number",
        "created_at",
        "updated_at",
        "subtotal",
        "total_amount",
        "shipped_at",
        "delivered_at",
    ]
    raw_id_fields: ClassVar[list] = ["user"]
    inlines: ClassVar[list] = [OrderItemInline]

    fieldsets = (
        (
            "Order Information",
            {
                "fields": ("order_number", "user", "status", "payment_status"),
            },
        ),
        (
            "Contact Information",
            {
                "fields": ("email", "phone_number"),
            },
        ),
        (
            "Shipping Address",
            {
                "fields": (
                    "shipping_first_name",
                    "shipping_last_name",
                    "shipping_address_line_1",
                    "shipping_address_line_2",
                    "shipping_city",
                    "shipping_state",
                    "shipping_postal_code",
                    "shipping_country",
                ),
            },
        ),
        (
            "Billing Address",
            {
                "fields": (
                    "billing_same_as_shipping",
                    "billing_first_name",
                    "billing_last_name",
                    "billing_address_line_1",
                    "billing_address_line_2",
                    "billing_city",
                    "billing_state",
                    "billing_postal_code",
                    "billing_country",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Financial Information",
            {
                "fields": (
                    "subtotal",
                    "tax_amount",
                    "shipping_cost",
                    "discount_amount",
                    "total_amount",
                ),
            },
        ),
        (
            "Fulfillment",
            {
                "fields": (
                    "tracking_number",
                    "carrier",
                    "estimated_delivery_date",
                    "shipped_at",
                    "delivered_at",
                ),
            },
        ),
        (
            "Notes",
            {
                "fields": ("customer_notes", "notes"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def user_link(self, obj):
        """Create clickable link to user."""
        if obj.user:
            url = reverse("admin:accounts_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "-"

    user_link.short_description = "User"

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            "pending": "orange",
            "confirmed": "blue",
            "processing": "purple",
            "shipped": "green",
            "delivered": "darkgreen",
            "cancelled": "red",
            "returned": "brown",
            "refunded": "gray",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "Status"

    def payment_status_display(self, obj):
        """Display payment status with color coding."""
        colors = {
            "pending": "orange",
            "paid": "green",
            "failed": "red",
            "refunded": "gray",
            "partially_refunded": "brown",
        }
        color = colors.get(obj.payment_status, "black")
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_payment_status_display(),
        )

    payment_status_display.short_description = "Payment"

    def actions_display(self, obj):
        """Display available actions for the order."""
        actions = []

        if obj.can_be_cancelled():
            actions.append('<span style="color: red;">Can Cancel</span>')

        if obj.can_be_shipped():
            actions.append('<span style="color: green;">Can Ship</span>')

        return format_html(" | ".join(actions)) if actions else "-"

    actions_display.short_description = "Available Actions"

    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related("user")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin interface for OrderItem model."""

    list_display: ClassVar[list] = [
        "id",
        "order_link",
        "product_link",
        "product_name",
        "quantity",
        "price",
        "total_price",
    ]
    list_filter: ClassVar[list] = ["created_at", "updated_at"]
    search_fields: ClassVar[list] = [
        "order__order_number",
        "product__name",
        "product__sku",
        "product_name",
        "product_sku",
    ]
    readonly_fields: ClassVar[list] = [
        "id",
        "product_name",
        "product_sku",
        "total_price",
        "created_at",
        "updated_at",
    ]
    raw_id_fields: ClassVar[list] = ["order", "product"]

    def order_link(self, obj):
        """Create clickable link to order."""
        url = reverse("admin:orders_order_change", args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)

    order_link.short_description = "Order"

    def product_link(self, obj):
        """Create clickable link to product."""
        if obj.product:
            url = reverse("admin:products_product_change", args=[obj.product.id])
            return format_html('<a href="{}">{}</a>', url, obj.product.sku)
        return obj.product_sku

    product_link.short_description = "Product"

    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related("order", "product")


# Custom admin actions
def mark_orders_as_shipped(modeladmin, request, queryset):
    """Bulk action to mark orders as shipped."""
    updated = 0
    for order in queryset:
        if order.can_be_shipped():
            order.status = Order.OrderStatus.SHIPPED
            order.shipped_at = timezone.now()
            order.save(update_fields=["status", "shipped_at", "updated_at"])
            updated += 1

    modeladmin.message_user(
        request,
        f"Successfully marked {updated} orders as shipped.",
    )


def mark_orders_as_delivered(modeladmin, request, queryset):
    """Bulk action to mark orders as delivered."""
    updated = 0
    for order in queryset:
        if order.status == Order.OrderStatus.SHIPPED:
            order.status = Order.OrderStatus.DELIVERED
            order.delivered_at = timezone.now()
            order.save(update_fields=["status", "delivered_at", "updated_at"])
            updated += 1

    modeladmin.message_user(
        request,
        f"Successfully marked {updated} orders as delivered.",
    )


# Add custom actions to OrderAdmin
mark_orders_as_shipped.short_description = "Mark selected orders as shipped"
mark_orders_as_delivered.short_description = "Mark selected orders as delivered"

OrderAdmin.actions = [mark_orders_as_shipped, mark_orders_as_delivered]
