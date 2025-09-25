# apps/orders/views.py

"""
Views for the order management system.
Handles cart operations, order creation, and order management.
"""

from datetime import timedelta
from typing import ClassVar

import structlog
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (OpenApiParameter, extend_schema,
                                   extend_schema_view)
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from apps.core.pagination import StandardResultsSetPagination
from apps.core.views import BaseViewSet
from apps.orders.models import Cart, CartItem, Order
from apps.orders.serializers import (AddToCartSerializer, CartSerializer,
                                     OrderCancelSerializer,
                                     OrderCreateSerializer, OrderSerializer,
                                     OrderShipmentSerializer,
                                     OrderSummarySerializer,
                                     OrderTrackingSerializer,
                                     OrderUpdateSerializer,
                                     ProductAvailabilitySerializer,
                                     UpdateCartItemSerializer)
from apps.orders.tasks import (send_order_confirmation_email_task,
                               send_shipping_notification_task)
from apps.orders.utils import InventoryManager
from apps.products.models import Product

from .filters import OrderFilter
from .permissions import IsOrderOwnerOrAdmin

User = get_user_model()
logger = structlog.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Get user's cart",
        description="Retrieve the current user's cart with all items and totals.",
    ),
    create=extend_schema(
        summary="Create or get cart",
        description="Create a new cart or get existing cart for the user.",
    ),
)
class CartViewSet(BaseViewSet):
    """
    ViewSet for managing shopping carts.
    Handles cart creation, item management, and totals calculation.
    """

    serializer_class = CartSerializer
    permission_classes: ClassVar[list] = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Get cart for current user or session."""
        if self.request.user.is_authenticated:
            return Cart.objects.filter(user=self.request.user)

        # For anonymous users, filter by session
        session_key = self.request.session.session_key
        if session_key:
            return Cart.objects.filter(session_key=session_key, user__isnull=True)

        return Cart.objects.none()

    def get_or_create_cart(self):
        """Get or create cart for current user/session."""
        if self.request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(
                user=self.request.user, defaults={"expires_at": None}
            )
        else:
            # Ensure session exists
            if not self.request.session.session_key:
                self.request.session.create()

            session_key = self.request.session.session_key
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                user__isnull=True,
                defaults={"expires_at": timezone.now() + timedelta(days=30)},
            )

        return cart, created

    def list(self, request, *args, **kwargs):
        """Get current cart."""
        try:
            cart, _ = self.get_or_create_cart()
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving cart: {e}")
            return Response(
                {"error": "Failed to retrieve cart"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        request=AddToCartSerializer,
        responses={200: CartSerializer},
        summary="Add item to cart",
        description="Add a product to the cart or update quantity if already exists.",
    )
    @action(detail=False, methods=["post"])
    def add_item(self, request):
        """Add item to cart."""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cart, _ = self.get_or_create_cart()

            product = Product.objects.get(id=serializer.validated_data["product_id"])
            quantity = serializer.validated_data["quantity"]

            cart.add_item(product, quantity)

            logger.info(
                f"Added {quantity}x {product.name} to cart",
                extra={
                    "user_id": getattr(request.user, "id", None),
                    "product_id": str(product.id),
                    "quantity": quantity,
                },
            )

            cart_serializer = CartSerializer(cart, context={"request": request})
            return Response(cart_serializer.data)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error adding item to cart: {e}")
            return Response(
                {"error": "Failed to add item to cart"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        request=UpdateCartItemSerializer,
        responses={200: CartSerializer},
        summary="Update cart item quantity",
        description="Update the quantity of a specific item in the cart. Set quantity to 0 to remove item.",
    )
    @action(detail=False, methods=["patch"], url_path="items/(?P<product_id>[^/.]+)")
    def update_item(self, request, product_id=None):
        """Update cart item quantity."""
        try:
            cart, _ = self.get_or_create_cart()
            cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)

            serializer = UpdateCartItemSerializer(
                cart_item,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)

            quantity = serializer.validated_data["quantity"]

            if quantity == 0:
                # Remove item from cart
                product_name = cart_item.product.name
                cart_item.delete()

                logger.info(
                    f"Removed {product_name} from cart",
                    extra={
                        "user_id": getattr(request.user, "id", None),
                        "product_id": product_id,
                    },
                )
            else:
                # Update quantity
                cart_item.quantity = quantity
                cart_item.save(update_fields=["quantity", "updated_at"])

                logger.info(
                    f"Updated cart item quantity to {quantity}",
                    extra={
                        "user_id": getattr(request.user, "id", None),
                        "product_id": product_id,
                        "quantity": quantity,
                    },
                )

            cart.refresh_from_db()
            cart_serializer = CartSerializer(cart, context={"request": request})
            return Response(cart_serializer.data)

        except CartItem.DoesNotExist:
            return Response(
                {"error": "Item not found in cart"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error updating cart item: {e}")
            return Response(
                {"error": "Failed to update cart item"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        responses={200: CartSerializer},
        summary="Remove item from cart",
        description="Remove a specific item from the cart completely.",
    )
    @action(detail=False, methods=["delete"], url_path="items/(?P<product_id>[^/.]+)")
    def remove_item(self, request, product_id=None):
        """Remove item from cart."""
        try:
            cart, _ = self.get_or_create_cart()
            cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)

            product_name = cart_item.product.name
            cart_item.delete()

            logger.info(
                f"Removed {product_name} from cart",
                extra={
                    "user_id": getattr(request.user, "id", None),
                    "product_id": product_id,
                },
            )

            cart.refresh_from_db()
            cart_serializer = CartSerializer(cart, context={"request": request})
            return Response(cart_serializer.data)

        except CartItem.DoesNotExist:
            return Response(
                {"error": "Item not found in cart"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error removing cart item: {e}")
            return Response(
                {"error": "Failed to remove cart item"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        responses={200: CartSerializer},
        summary="Clear cart",
        description="Remove all items from the cart.",
    )
    @action(detail=False, methods=["delete"])
    def clear(self, request):
        """Clear all items from cart."""
        try:
            cart, _ = self.get_or_create_cart()
            items_count = cart.items.count()
            cart.clear()

            logger.info(
                f"Cleared cart with {items_count} items",
                extra={"user_id": getattr(request.user, "id", None)},
            )

            cart_serializer = CartSerializer(cart, context={"request": request})
            return Response(cart_serializer.data)

        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return Response(
                {"error": "Failed to clear cart"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        responses={200: ProductAvailabilitySerializer(many=True)},
        summary="Check cart items availability",
        description="Check if all cart items are still available in requested quantities.",
    )
    @action(detail=False, methods=["get"])
    def check_availability(self, request):
        """Check availability of all cart items."""
        try:
            cart, _ = self.get_or_create_cart()

            items = []
            for cart_item in cart.items.all():
                items.append(
                    {
                        "product_id": str(cart_item.product.id),
                        "quantity": cart_item.quantity,
                    },
                )

            availability_results = InventoryManager.check_availability(items)

            serializer = ProductAvailabilitySerializer(availability_results, many=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error checking cart availability: {e}")
            return Response(
                {"error": "Failed to check availability"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema_view(
    list=extend_schema(
        summary="List orders",
        description="List orders for the authenticated user or all orders for admin users.",
        parameters=[
            OpenApiParameter("status", str, description="Filter by order status"),
            OpenApiParameter(
                "payment_status",
                str,
                description="Filter by payment status",
            ),
            OpenApiParameter(
                "date_from",
                str,
                description="Filter orders from date (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                "date_to",
                str,
                description="Filter orders to date (YYYY-MM-DD)",
            ),
        ],
    ),
    create=extend_schema(
        summary="Create order",
        description="Create a new order from cart items.",
        request=OrderCreateSerializer,
        responses={201: OrderSerializer},
    ),
    retrieve=extend_schema(
        summary="Get order details",
        description="Retrieve detailed information about a specific order.",
    ),
    update=extend_schema(
        summary="Update order",
        description="Update order details (admin only).",
    ),
)
class OrderViewSet(BaseViewSet):
    """
    ViewSet for managing orders.
    Handles order creation, retrieval, and status updates.
    """

    serializer_class = OrderSerializer
    permission_classes: ClassVar[list] = [IsAuthenticated, IsOrderOwnerOrAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends: ClassVar[list] = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]
    filterset_class: ClassVar[list] = OrderFilter
    search_fields: ClassVar[list] = [
        "order_number",
        "email",
        "shipping_first_name",
        "shipping_last_name",
    ]
    ordering_fields: ClassVar[list] = [
        "created_at",
        "updated_at",
        "total_amount",
        "status",
    ]
    ordering: ClassVar[list] = ["-created_at"]

    def get_queryset(self):
        """Get orders based on user permissions."""
        if self.request.user.is_staff:
            # Admin users can see all orders
            return Order.objects.select_related("user").prefetch_related(
                "items__product",
            )
        else:
            # Regular users can only see their own orders
            return (
                Order.objects.filter(user=self.request.user)
                .select_related("user")
                .prefetch_related("items__product")
            )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return OrderCreateSerializer
        elif self.action == "update" or self.action == "partial_update":
            return OrderUpdateSerializer
        elif self.action == "list":
            return OrderSummarySerializer
        elif self.action == "ship":
            return OrderShipmentSerializer
        elif self.action == "cancel":
            return OrderCancelSerializer
        elif self.action == "track":
            return OrderTrackingSerializer
        return OrderSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create order from cart items."""
        try:
            # Get user's cart
            if request.user.is_authenticated:
                cart = get_object_or_404(Cart, user=request.user)
            else:
                session_key = request.session.session_key
                if not session_key:
                    return Response(
                        {"error": "No active cart found"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                cart = get_object_or_404(
                    Cart,
                    session_key=session_key,
                    user__isnull=True,
                )

            if not cart.items.exists():
                return Response(
                    {"error": "Cart is empty"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate order data
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Create order from cart
            order = serializer.create_order_from_cart(request.user, cart)

            logger.info(
                f"Order created: {order.order_number}",
                extra={
                    "user_id": str(request.user.id),
                    "order_id": str(order.id),
                    "total_amount": str(order.total_amount),
                },
            )

            # Send confirmation email asynchronously
            send_order_confirmation_email_task.delay(str(order.id))

            # Return created order
            response_serializer = OrderSerializer(order, context={"request": request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return Response(
                {"error": "Failed to create order"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        request=OrderShipmentSerializer,
        responses={200: OrderSerializer},
        summary="Ship order",
        description="Mark order as shipped and add tracking information (admin only).",
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def ship(self, request, pk=None):
        """Ship an order with tracking information."""
        if not request.user.is_staff:
            return Response(
                {"error": "Admin permission required"},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = self.get_object()
        serializer = OrderShipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_order = serializer.ship_order(order)

            logger.info(
                f"Order shipped: {order.order_number}",
                extra={
                    "order_id": str(order.id),
                    "tracking_number": updated_order.tracking_number,
                    "carrier": updated_order.carrier,
                },
            )

            # Send shipping notification
            send_shipping_notification_task.delay(str(order.id))

            response_serializer = OrderSerializer(
                updated_order,
                context={"request": request},
            )
            return Response(response_serializer.data)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=OrderCancelSerializer,
        responses={200: OrderSerializer},
        summary="Cancel order",
        description="Cancel an order and restore inventory.",
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an order."""
        order = self.get_object()

        # Check permissions - users can cancel their own orders, admins can cancel any
        if order.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "You can only cancel your own orders"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_order = serializer.cancel_order(order)

            logger.info(
                f"Order cancelled: {order.order_number}",
                extra={
                    "order_id": str(order.id),
                    "cancelled_by": str(request.user.id),
                    "reason": serializer.validated_data.get("reason", ""),
                },
            )

            response_serializer = OrderSerializer(
                updated_order,
                context={"request": request},
            )
            return Response(response_serializer.data)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={200: OrderTrackingSerializer},
        summary="Track order",
        description="Get tracking information for an order.",
    )
    @action(detail=True, methods=["get"])
    def track(self, request, pk=None):
        """Get order tracking information."""
        order = self.get_object()
        serializer = OrderTrackingSerializer(order, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        responses={200: OrderSerializer},
        summary="Mark as delivered",
        description="Mark order as delivered (admin only).",
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def delivered(self, request, pk=None):
        """Mark order as delivered."""
        if not request.user.is_staff:
            return Response(
                {"error": "Admin permission required"},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = self.get_object()

        try:
            order.mark_as_delivered()

            logger.info(
                f"Order marked as delivered: {order.order_number}",
                extra={"order_id": str(order.id)},
            )

            serializer = OrderSerializer(order, context={"request": request})
            return Response(serializer.data)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={200: dict},
        summary="Order statistics",
        description="Get order statistics (admin only).",
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def statistics(self, request):
        """Get order statistics."""
        if not request.user.is_staff:
            return Response(
                {"error": "Admin permission required"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            # Calculate various statistics
            total_orders = Order.objects.count()

            # Orders by status
            status_counts = Order.objects.values("status").annotate(count=Count("id"))
            status_stats = {item["status"]: item["count"] for item in status_counts}

            # Revenue statistics
            revenue_stats = Order.objects.filter(
                payment_status=Order.PaymentStatus.PAID,
            ).aggregate(
                total_revenue=Sum("total_amount"),
                average_order_value=(
                    Sum("total_amount") / Count("id") if Count("id") > 0 else 0
                ),
            )

            # Recent orders (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_orders = Order.objects.filter(
                created_at__gte=thirty_days_ago,
            ).count()

            # Orders needing attention
            needs_shipping = Order.objects.filter(
                status__in=[Order.OrderStatus.CONFIRMED, Order.OrderStatus.PROCESSING],
                payment_status=Order.PaymentStatus.PAID,
            ).count()

            return Response(
                {
                    "total_orders": total_orders,
                    "status_breakdown": status_stats,
                    "total_revenue": revenue_stats["total_revenue"] or 0,
                    "average_order_value": revenue_stats["average_order_value"] or 0,
                    "recent_orders_30_days": recent_orders,
                    "orders_needing_shipment": needs_shipping,
                },
            )

        except Exception as e:
            logger.error(f"Error calculating order statistics: {e}")
            return Response(
                {"error": "Failed to calculate statistics"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
