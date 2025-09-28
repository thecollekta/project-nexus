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
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (OpenApiParameter, OpenApiResponse,
                                   extend_schema, extend_schema_view)
from rest_framework import filters, permissions, status
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
        responses={
            200: CartSerializer,
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Cart"],
    ),
    create=extend_schema(
        summary="Create or get cart",
        description="Create a new cart or get existing cart for the user.",
        responses={
            201: CartSerializer,
            400: OpenApiResponse(description="Invalid input"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Cart"],
    ),
)
class CartViewSet(BaseViewSet):
    """
    ViewSet for managing shopping carts.
    Handles cart creation, item management, and totals calculation.
    """

    serializer_class = CartSerializer
    permission_classes: ClassVar[list] = [IsAuthenticatedOrReadOnly]
    queryset = Cart.objects.none()

    def get_queryset(self):
        """Get cart for current user or session."""
        if getattr(self, "swagger_fake_view", False):
            return Cart.objects.none()

        if self.request.user.is_authenticated:
            return Cart.objects.filter(user=self.request.user)

        # For anonymous users, filter by session
        if hasattr(self.request, "session") and self.request.session.session_key:
            session_key = self.request.session.session_key
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
        responses={
            200: CartSerializer,
            400: OpenApiResponse(description="Invalid product or quantity"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Product not found"),
        },
        summary="Add item to cart",
        description="Add a product to the cart or update quantity if already exists.",
        tags=["Cart"],
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
        responses={
            200: CartSerializer,
            400: OpenApiResponse(description="Invalid quantity"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Cart item not found"),
        },
        parameters=[
            OpenApiParameter(
                name="product_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Product ID to update",
            ),
        ],
        summary="Update cart item quantity",
        description="Update the quantity of a specific item in the cart. Set quantity to 0 to remove item.",
        tags=["Cart"],
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
        responses={
            200: CartSerializer,
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Cart item not found"),
        },
        parameters=[
            OpenApiParameter(
                name="product_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Product ID to remove",
            ),
        ],
        summary="Remove item from cart",
        description="Remove a specific item from the cart completely.",
        tags=["Cart"],
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
        responses={
            200: CartSerializer,
            401: OpenApiResponse(description="Authentication required"),
        },
        summary="Clear cart",
        description="Remove all items from the cart.",
        tags=["Cart"],
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
        responses={
            200: ProductAvailabilitySerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
        summary="Check cart items availability",
        description="Check if all cart items are still available in requested quantities.",
        tags=["Cart"],
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
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                description="Filter by order status",
                required=False,
            ),
            OpenApiParameter(
                name="payment_status",
                type=OpenApiTypes.STR,
                description="Filter by payment status",
                required=False,
            ),
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                description="Filter orders from date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                description="Filter orders to date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="min_amount",
                type=OpenApiTypes.FLOAT,
                description="Minimum order amount",
                required=False,
            ),
            OpenApiParameter(
                name="max_amount",
                type=OpenApiTypes.FLOAT,
                description="Maximum order amount",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                description="Search in order number, email, or customer name",
                required=False,
            ),
        ],
        responses={
            200: OrderSummarySerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Orders"],
    ),
    retrieve=extend_schema(
        summary="Get order details",
        description="Retrieve detailed information about a specific order.",
        responses={
            200: OrderSerializer,
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not order owner or admin"),
            404: OpenApiResponse(description="Order not found"),
        },
        tags=["Orders"],
    ),
    create=extend_schema(
        summary="Create order",
        description="Create a new order from cart items.",
        request=OrderCreateSerializer,
        responses={
            201: OrderSerializer,
            400: OpenApiResponse(description="Invalid input or cart empty"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Orders"],
    ),
    update=extend_schema(
        summary="Update order",
        description="Update order details (admin only).",
        request=OrderUpdateSerializer,
        responses={
            200: OrderSerializer,
            400: OpenApiResponse(description="Invalid input"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
            404: OpenApiResponse(description="Order not found"),
        },
        tags=["Orders"],
    ),
    partial_update=extend_schema(
        summary="Partial update order",
        description="Partially update order details (admin only).",
        request=OrderUpdateSerializer,
        responses={
            200: OrderSerializer,
            400: OpenApiResponse(description="Invalid input"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
            404: OpenApiResponse(description="Order not found"),
        },
        tags=["Orders"],
    ),
    destroy=extend_schema(
        summary="Delete order",
        description="Delete an order (admin only).",
        responses={
            204: OpenApiResponse(description="Order deleted successfully"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
            404: OpenApiResponse(description="Order not found"),
        },
        tags=["Orders"],
    ),
)
class OrderViewSet(BaseViewSet):
    """
    ViewSet for managing orders.
    Handles order creation, retrieval, and status updates.
    """

    serializer_class = OrderSerializer
    permission_classes: ClassVar[list] = [
        permissions.IsAuthenticated,
        IsOrderOwnerOrAdmin,
    ]
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
    queryset = Order.objects.none()

    def get_queryset(self):
        """Get orders based on user permissions."""
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()

        if self.request.user.is_staff:
            # Admin users can see all orders
            return Order.objects.select_related("user").prefetch_related(
                "items__product",
            )
        else:
            # Only return orders for authenticated users
            if self.request.user.is_authenticated:
                return (
                    Order.objects.filter(user=self.request.user)
                    .select_related("user")
                    .prefetch_related("items__product")
                )
            return Order.objects.none()

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
        responses={
            200: OrderSerializer,
            400: OpenApiResponse(
                description="Invalid tracking data or order cannot be shipped"
            ),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
            404: OpenApiResponse(description="Order not found"),
        },
        summary="Ship order",
        description="Mark order as shipped and add tracking information (admin only).",
        tags=["Orders", "Admin"],
    )
    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
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
        responses={
            200: OrderSerializer,
            400: OpenApiResponse(description="Order cannot be cancelled"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not order owner or admin"),
            404: OpenApiResponse(description="Order not found"),
        },
        summary="Cancel order",
        description="Cancel an order and restore inventory.",
        tags=["Orders"],
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
        responses={
            200: OrderTrackingSerializer,
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not order owner or admin"),
            404: OpenApiResponse(description="Order not found"),
        },
        summary="Track order",
        description="Get tracking information for an order.",
        tags=["Orders"],
    )
    @action(detail=True, methods=["get"])
    def track(self, request, pk=None):
        """Get order tracking information."""
        order = self.get_object()
        serializer = OrderTrackingSerializer(order, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        responses={
            200: OrderSerializer,
            400: OpenApiResponse(description="Order cannot be marked as delivered"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
            404: OpenApiResponse(description="Order not found"),
        },
        summary="Mark as delivered",
        description="Mark order as delivered (admin only).",
        tags=["Orders", "Admin"],
    )
    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
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
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total_orders": {"type": "integer"},
                    "status_breakdown": {
                        "type": "object",
                        "additionalProperties": {"type": "integer"},
                    },
                    "total_revenue": {"type": "number"},
                    "average_order_value": {"type": "number"},
                    "recent_orders_30_days": {"type": "integer"},
                    "orders_needing_shipment": {"type": "integer"},
                },
            },
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
        },
        summary="Order statistics",
        description="Get order statistics (admin only).",
        tags=["Orders", "Admin"],
    )
    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="days",
                type=OpenApiTypes.INT,
                description="Number of days for recent orders (default: 30)",
                required=False,
            ),
        ],
        responses={
            200: OrderSummarySerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
        },
        summary="Get recent orders",
        description="Get orders from the last N days (admin only).",
        tags=["Orders", "Admin"],
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def recent(self, request):
        """Get recent orders."""
        try:
            days = int(request.query_params.get("days", 30))
            cutoff_date = timezone.now() - timedelta(days=days)

            queryset = self.get_queryset().filter(created_at__gte=cutoff_date)
            queryset = self.filter_queryset(queryset)

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        except ValueError:
            return Response(
                {"error": "Invalid days parameter"}, status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                description="Order status to filter by",
                required=True,
            ),
        ],
        responses={
            200: OrderSummarySerializer(many=True),
            400: OpenApiResponse(description="Invalid status parameter"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
        },
        summary="Get orders by status",
        description="Get orders filtered by specific status (admin only).",
        tags=["Orders", "Admin"],
    )
    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def by_status(self, request):
        """Get orders by status."""
        status_param = request.query_params.get("status")
        if not status_param:
            return Response(
                {"error": "Status parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate status
        valid_statuses = [choice[0] for choice in Order.OrderStatus.choices]
        if status_param not in valid_statuses:
            return Response(
                {
                    "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(status=status_param)
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
