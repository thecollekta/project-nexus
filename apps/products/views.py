# apps/products/views.py

"""
ViewSets for the products app.

Provides comprehensive API endpoints for products, categories, and related models
with proper filtering, search, and pagination capabilities.
"""

from decimal import Decimal, InvalidOperation
from typing import ClassVar

import structlog
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.core.pagination import LargeResultsSetPagination, StandardResultsSetPagination
from apps.core.views import BaseReadOnlyViewSet, BaseViewSet
from apps.products.filters import CategoryFilter, ProductFilter
from apps.products.models import (
    Category,
    Product,
    ProductImage,
    ProductReview,
    ProductSpecification,
)
from apps.products.permissions import IsOwnerOrReadOnly
from apps.products.serializers import (
    CategoryDetailSerializer,
    CategoryListSerializer,
    CategorySerializerSelector,
    ProductCreateUpdateSerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    ProductInventorySerializer,
    ProductListSerializer,
    ProductPricingSerializer,
    ProductReviewSerializer,
    ProductSerializerSelector,
    ProductSpecificationSerializer,
    StockAdjustmentSerializer,
)

# Set up logging
logger = structlog.get_logger(__name__)


class BaseProductCategoryMixin:
    """Base mixin for common product and category functionality."""

    def _get_paginated_response(
        self, queryset, request, serializer_class, context=None
    ):
        """Common method to handle paginated responses."""
        context = context or {}
        context["request"] = request

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializer_class(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)

        serializer = serializer_class(queryset, many=True, context=context)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List all categories",
        description="Retrieve a paginated list of all product categories with optional filtering.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Filter by parent category ID (null for root categories)",
                required=True,
            ),
            OpenApiParameter(
                name="in_stock",
                type=OpenApiTypes.BOOL,
                description="Filter products in stock",
                required=False,
            ),
            OpenApiParameter(
                name="min_price",
                type=OpenApiTypes.FLOAT,
                description="Minimum product price",
                required=False,
            ),
            OpenApiParameter(
                name="max_price",
                type=OpenApiTypes.FLOAT,
                description="Maximum product price",
                required=False,
            ),
            OpenApiParameter(
                name="is_featured",
                type=bool,
                description="Filter featured categories",
            ),
            OpenApiParameter(
                name="search",
                type=str,
                description="Search by name or description",
            ),
        ],
        responses={
            200: ProductListSerializer(many=True),
            400: OpenApiResponse(
                description="Invalid UUID format or parameters",
            ),
            404: OpenApiResponse(
                description="Category not found",
            ),
        },
        tags=["Categories"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a category",
        description="Get detailed information about a specific category by ID.",
        responses={
            200: CategoryDetailSerializer,
            404: OpenApiResponse(description="Category not found"),
        },
    ),
    create=extend_schema(
        summary="Create a category",
        description="Create a new product category.",
        responses={
            201: CategoryDetailSerializer,
            400: OpenApiResponse(description="Invalid input"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
        },
    ),
    update=extend_schema(
        summary="Update a category",
        description="Update an existing category.",
        responses={
            200: CategoryDetailSerializer,
            400: OpenApiResponse(description="Invalid input"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Category not found"),
        },
    ),
    partial_update=extend_schema(
        summary="Partially update a category",
        description="Update specific fields of a category.",
        responses={
            200: CategoryDetailSerializer,
            400: OpenApiResponse(description="Invalid input"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Category not found"),
        },
    ),
    destroy=extend_schema(
        summary="Delete a category",
        description="Delete a category by ID.",
        responses={
            204: OpenApiResponse(description="Category deleted"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Category not found"),
        },
    ),
    roots=extend_schema(
        summary="List root categories",
        description="Get a list of all root-level categories (categories without parents).",
        responses={
            200: CategoryListSerializer(many=True),
        },
    ),
    featured=extend_schema(
        summary="List featured categories",
        description="Get a list of categories marked as featured.",
        responses={
            200: CategoryListSerializer(many=True),
        },
    ),
    children=extend_schema(
        summary="List category children",
        description="Get a list of direct child categories for a specific category.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Parent category ID",
            ),
        ],
        responses={
            200: CategoryListSerializer(many=True),
            404: OpenApiResponse(description="Parent category not found"),
        },
    ),
    products=extend_schema(
        summary="List category products",
        description="Get a paginated list of products in a specific category.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Category ID",
            ),
            OpenApiParameter(
                name="in_stock",
                type=bool,
                description="Filter products in stock",
                required=False,
            ),
            OpenApiParameter(
                name="min_price",
                type=float,
                description="Minimum product price",
                required=False,
            ),
            OpenApiParameter(
                name="max_price",
                type=float,
                description="Maximum product price",
                required=False,
            ),
        ],
        responses={
            200: ProductListSerializer(many=True),
            404: OpenApiResponse(description="Category not found"),
        },
    ),
)
@extend_schema(tags=["Categories"])
class CategoryViewSet(BaseViewSet, BaseProductCategoryMixin):
    """
    ViewSet for managing product categories.

    Provides CRUD operations for categories with hierarchical support,
    filtering, and search capabilities.
    """

    queryset = Category.objects.all()
    filterset_class = CategoryFilter
    filter_backends: ClassVar[list] = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields: ClassVar[list[str]] = ["name", "description"]
    ordering_fields: ClassVar[list[str]] = ["name", "sort_order", "created_at"]
    ordering: ClassVar[list[str]] = ["sort_order", "name"]
    permission_classes: ClassVar[list] = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        return CategorySerializerSelector.get_serializer_class(
            request=self.request,
            action=self.action,
        )

    def get_queryset(self) -> QuerySet[Category]:
        """Optimize queryset with proper prefetching."""
        queryset = super().get_queryset()

        if self.action == "list":
            # Optimized for list view
            return queryset.select_related("parent").prefetch_related(
                Prefetch(
                    "children",
                    queryset=Category.objects.filter(is_active=True).order_by(
                        "sort_order",
                    ),
                ),
            )
        if self.action == "retrieve":
            # Optimized for detail view
            return queryset.select_related("parent").prefetch_related(
                Prefetch(
                    "children",
                    queryset=Category.objects.filter(is_active=True).order_by(
                        "sort_order",
                    ),
                ),
                Prefetch(
                    "products",
                    queryset=Product.objects.filter(is_active=True).select_related(
                        "category",
                    ),
                ),
            )

        return queryset

    @extend_schema(
        summary="Get root categories",
        description="Retrieve all root-level categories (categories without parent).",
        responses={200: CategoryListSerializer(many=True)},
        tags=["Categories"],
    )
    @action(detail=False, methods=["get"])
    def roots(self, request):
        """Get all root categories."""
        queryset = self.get_queryset().filter(parent__isnull=True)
        queryset = self.filter_queryset(queryset)
        return self._get_paginated_response(queryset, request, CategoryListSerializer)

    @extend_schema(
        summary="Get featured categories",
        description="Retrieve all featured categories.",
        responses={200: CategoryListSerializer(many=True)},
        tags=["Categories"],
    )
    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Get all featured categories."""
        queryset = self.get_queryset().filter(is_featured=True)
        queryset = self.filter_queryset(queryset)
        return self._get_paginated_response(queryset, request, CategoryListSerializer)

    @extend_schema(
        summary="Get category children",
        description="Retrieve all direct children of a specific category.",
        responses={200: CategoryListSerializer(many=True)},
        tags=["Categories"],
    )
    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        """Get direct children of a category."""
        category = self.get_object()
        queryset = category.children.filter(is_active=True).order_by(
            "sort_order",
            "name",
        )
        return self._get_paginated_response(queryset, request, CategoryListSerializer)

    @extend_schema(
        summary="Get category products",
        description="Retrieve all products in a specific category.",
        responses={200: ProductListSerializer(many=True)},
        tags=["Categories"],
    )
    @action(detail=True, methods=["get"])
    def products(self, request, pk=None):
        """Get all products in a category."""
        category = self.get_object()
        queryset = category.products.filter(is_active=True).select_related("category")

        # Apply filters from query parameters
        queryset = self._apply_product_filters(queryset, request.query_params)

        return self._get_paginated_response(queryset, request, ProductListSerializer)

    def _apply_product_filters(self, queryset, query_params):
        """Apply common product filters to queryset."""
        in_stock = query_params.get("in_stock")
        min_price = query_params.get("min_price")
        max_price = query_params.get("max_price")

        if in_stock and in_stock.lower() == "true":
            queryset = queryset.filter(stock_quantity__gt=0)

        if min_price:
            try:
                queryset = queryset.filter(price__amount__gte=Decimal(min_price))
            except (ValueError, InvalidOperation):
                pass

        if max_price:
            try:
                queryset = queryset.filter(price__amount__lte=Decimal(max_price))
            except (ValueError, InvalidOperation):
                pass

        return queryset


@extend_schema(tags=["Products"])
class ProductViewSet(BaseViewSet, BaseProductCategoryMixin):
    """
    ViewSet for managing products.

    Provides comprehensive CRUD operations for products with advanced
    filtering, search, and related data management.
    """

    queryset = Product.objects.all()
    filterset_class = ProductFilter
    filter_backends: ClassVar[list] = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields: ClassVar[list[str]] = [
        "name",
        "description",
        "short_description",
        "sku",
        "category__name",
    ]
    ordering_fields: ClassVar[list[str]] = [
        "name",
        "price",
        "stock_quantity",
        "created_at",
        "updated_at",
    ]
    ordering: ClassVar[list[str]] = ["-created_at"]
    permission_classes: ClassVar[list] = [IsAuthenticatedOrReadOnly]
    pagination_class = LargeResultsSetPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        return ProductSerializerSelector.get_serializer_class(
            request=self.request,
            action=self.action,
        )

    def get_queryset(self) -> QuerySet[Product]:
        """Optimize queryset with proper prefetching."""
        queryset = super().get_queryset()

        if self.action == "list":
            # Optimized for list view
            return queryset.select_related("category").prefetch_related(
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.filter(is_active=True).order_by(
                        "sort_order",
                    ),
                ),
            )
        if self.action == "retrieve":
            # Optimized for detail view
            return queryset.select_related("category").prefetch_related(
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.filter(is_active=True).order_by(
                        "sort_order",
                    ),
                ),
                Prefetch(
                    "specifications",
                    queryset=ProductSpecification.objects.filter(
                        is_active=True,
                    ).order_by("sort_order"),
                ),
            )

        return queryset

    @extend_schema(
        summary="List products",
        description="Retrieve a paginated list of products with advanced filtering and search capabilities.",
        parameters=[
            OpenApiParameter(
                name="category",
                description="Filter by category ID",
                required=False,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="is_featured",
                description="Filter by featured status",
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name="in_stock",
                description="Filter by stock availability",
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name="min_price",
                description="Minimum price filter",
                required=False,
                type=OpenApiTypes.FLOAT,
            ),
            OpenApiParameter(
                name="max_price",
                description="Maximum price filter",
                required=False,
                type=OpenApiTypes.FLOAT,
            ),
            OpenApiParameter(
                name="search",
                description="Search in product name, description, and SKU",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="ordering",
                description="Which field to use when ordering the results",
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={200: ProductListSerializer(many=True)},
        tags=["Products"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve product",
        description="Get detailed information about a specific product including images, specifications, and reviews.",
        responses={
            200: ProductDetailSerializer,
            404: OpenApiResponse(description="Product not found"),
        },
        tags=["Products"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create product",
        description="Create a new product with images and specifications.",
        request=ProductCreateUpdateSerializer,
        responses={
            201: ProductDetailSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Products"],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update product",
        description="Update an existing product with all related data.",
        request=ProductCreateUpdateSerializer,
        responses={
            200: ProductDetailSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Product not found"),
        },
        tags=["Products"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partial update product",
        description="Partially update an existing product.",
        request=ProductCreateUpdateSerializer,
        responses={
            200: ProductDetailSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Product not found"),
        },
        tags=["Products"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete product",
        description="Soft delete a product (mark as inactive).",
        responses={
            204: OpenApiResponse(description="Product deleted successfully"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Product not found"),
        },
        tags=["Products"],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Get featured products",
        description="Retrieve all featured products with pagination and filtering.",
        parameters=[
            OpenApiParameter(
                name="category",
                description="Filter by category ID",
                required=False,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="in_stock",
                description="Filter by stock availability",
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name="min_price",
                description="Minimum price filter",
                required=False,
                type=OpenApiTypes.FLOAT,
            ),
            OpenApiParameter(
                name="max_price",
                description="Maximum price filter",
                required=False,
                type=OpenApiTypes.FLOAT,
            ),
            OpenApiParameter(
                name="search",
                description="Search in product name, description, and SKU",
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={
            200: ProductListSerializer(many=True),
            400: OpenApiResponse(description="Invalid filter parameters"),
        },
        tags=["Products"],
    )
    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Get all featured products."""
        queryset = self.get_queryset().filter(is_featured=True)
        queryset = self.filter_queryset(queryset)
        return self._get_paginated_response(queryset, request, ProductListSerializer)

    @extend_schema(
        summary="Get low stock products",
        description="Retrieve products with low stock levels (requires authentication).",
        parameters=[
            OpenApiParameter(
                name="threshold",
                description="Custom low stock threshold (overrides product's default)",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="category",
                description="Filter by category ID",
                required=False,
                type=OpenApiTypes.UUID,
            ),
        ],
        responses={
            200: ProductListSerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Products", "Inventory"],
    )
    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        """Get all products with low stock."""
        queryset = self.get_queryset().filter(
            track_inventory=True,
            stock_quantity__lte=models.F("low_stock_threshold"),
        )

        # Apply custom threshold if provided
        threshold = request.query_params.get("threshold")
        if threshold:
            try:
                threshold_value = int(threshold)
                queryset = queryset.filter(stock_quantity__lte=threshold_value)
            except ValueError:
                pass  # Use default threshold if invalid

        queryset = self.filter_queryset(queryset)
        return self._get_paginated_response(queryset, request, ProductListSerializer)

    @extend_schema(
        summary="Update product inventory",
        description="Update stock quantity and inventory settings for a product.",
        request=ProductInventorySerializer,
        responses={
            200: ProductInventorySerializer,
            400: OpenApiResponse(description="Invalid input data"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Product not found"),
        },
        tags=["Products", "Inventory"],
    )
    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
    def inventory(self, request, pk=None):
        """Update product inventory."""
        return self._update_product_with_logging(
            request,
            pk,
            ProductInventorySerializer,
            "product_inventory_updated",
            "stock_quantity",
        )

    @extend_schema(
        summary="Update product pricing",
        description="Update pricing information for a product including price, compare price, and cost price.",
        request=ProductPricingSerializer,
        responses={
            200: ProductPricingSerializer,
            400: OpenApiResponse(description="Invalid pricing data"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Product not found"),
        },
        tags=["Products", "Pricing"],
    )
    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
    def pricing(self, request, pk=None):
        """Update product pricing."""
        return self._update_product_with_logging(
            request, pk, ProductPricingSerializer, "product_pricing_updated", "price"
        )

    def _update_product_with_logging(
        self, request, pk, serializer_class, log_event, log_field
    ):
        """Common method to update product fields with logging."""
        product = self.get_object()
        serializer = serializer_class(
            product,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                # Log the update
                logger.info(
                    log_event,
                    product_id=product.id,
                    product_name=product.name,
                    **{f"new_{log_field}": serializer.validated_data.get(log_field)},
                    user_id=request.user.id if request.user.is_authenticated else None,
                )

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Adjust product stock",
        description="Increase or decrease product stock by a specific amount.",
        request=StockAdjustmentSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "previous_stock": {"type": "integer"},
                    "new_stock": {"type": "integer"},
                    "adjustment": {"type": "integer"},
                },
            },
            400: OpenApiResponse(
                description="Invalid quantity or business rule violation"
            ),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Product not found"),
        },
        tags=["Products", "Inventory"],
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def adjust_stock(self, request, pk=None):
        """Adjust product stock quantity."""
        product = self.get_object()
        serializer = StockAdjustmentSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity_str = request.data.get("quantity", "0")
            # Handle both integer and decimal strings
            quantity = int(Decimal(quantity_str))
            reason = request.data.get("reason", "Manual adjustment")
        except (TypeError, ValueError, InvalidOperation) as e:
            logger.error(
                f"Invalid quantity provided: {request.data.get('quantity')}, error: {e}"
            )
            return Response(
                {"error": "Invalid quantity provided. Must be a valid number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not product.track_inventory:
            return Response(
                {"error": "Inventory tracking is disabled for this product"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_stock = product.stock_quantity
        new_stock = max(0, previous_stock + quantity)

        # Validate we don't go negative
        if new_stock < 0:
            return Response(
                {"error": "Cannot reduce stock below zero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            product.stock_quantity = new_stock
            product.save(update_fields=["stock_quantity", "updated_at"])

            # Log stock adjustment
            logger.info(
                "product_stock_adjusted",
                product_id=product.id,
                product_name=product.name,
                previous_stock=previous_stock,
                new_stock=new_stock,
                adjustment=quantity,
                reason=reason,
                user_id=request.user.id,
            )

        return Response(
            {
                "message": "Stock adjusted successfully",
                "previous_stock": previous_stock,
                "new_stock": new_stock,
                "adjustment": quantity,
            },
        )

    @extend_schema(
        summary="Search products",
        description="Advanced product search with category filtering and price range.",
        parameters=[
            OpenApiParameter(
                name="q",
                description="Search query",
                required=True,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="category",
                description="Category ID to search within",
                required=False,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="min_price",
                description="Minimum price",
                required=False,
                type=OpenApiTypes.FLOAT,
            ),
            OpenApiParameter(
                name="max_price",
                description="Maximum price",
                required=False,
                type=OpenApiTypes.FLOAT,
            ),
            OpenApiParameter(
                name="in_stock",
                description="Filter by stock availability",
                required=False,
                type=OpenApiTypes.BOOL,
            ),
            OpenApiParameter(
                name="is_featured",
                description="Filter by featured status",
                required=False,
                type=OpenApiTypes.BOOL,
            ),
        ],
        responses={
            200: ProductListSerializer(many=True),
            400: OpenApiResponse(
                description="Search query is required or invalid parameters"
            ),
        },
        tags=["Products", "Search"],
    )
    @action(detail=False, methods=["get"])
    def search(self, request):
        """Advanced product search."""
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"error": "Search query is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Start with base queryset
        queryset = self.get_queryset()

        # Apply text search
        search_query = (
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(short_description__icontains=query)
            | Q(sku__icontains=query)
            | Q(category__name__icontains=query)
            | Q(specifications__name__icontains=query)
            | Q(specifications__value__icontains=query)
        )
        queryset = queryset.filter(search_query).distinct()

        # Apply additional filters with proper error handling
        queryset = self._apply_search_filters(queryset, request.query_params)

        # Apply ordering
        queryset = queryset.order_by("-is_featured", "name")

        return self._get_paginated_response(queryset, request, ProductListSerializer)

    def _apply_search_filters(self, queryset, query_params):
        """Apply search-specific filters to queryset."""
        category_id = query_params.get("category")
        if category_id:
            try:
                queryset = queryset.filter(category_id=category_id)
            except (ValueError, ValidationError):
                logger.warning(f"Invalid category ID: {category_id}")

        min_price = query_params.get("min_price")
        if min_price:
            try:
                min_price_decimal = Decimal(min_price)
                queryset = queryset.filter(price__amount__gte=min_price_decimal)
            except (InvalidOperation, ValueError, TypeError) as e:
                logger.warning(f"Invalid min_price parameter: {min_price}, error: {e}")
                # Note: We can't return Response here, so we just log and continue

        max_price = query_params.get("max_price")
        if max_price:
            try:
                max_price_decimal = Decimal(max_price)
                queryset = queryset.filter(price__amount__lte=max_price_decimal)
            except (InvalidOperation, ValueError, TypeError) as e:
                logger.warning(f"Invalid max_price parameter: {max_price}, error: {e}")
                # Note: We can't return Response here, so we just log and continue

        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List product images",
        description="Retrieve all images for products.",
        tags=["Product Images"],
    ),
    retrieve=extend_schema(
        summary="Get product image",
        description="Retrieve a specific product image.",
        tags=["Product Images"],
    ),
    create=extend_schema(
        summary="Add product image",
        description="Add a new image to a product.",
        tags=["Product Images"],
    ),
    update=extend_schema(
        summary="Update product image",
        description="Update product image details.",
        tags=["Product Images"],
    ),
    destroy=extend_schema(
        summary="Delete product image",
        description="Remove an image from a product.",
        tags=["Product Images"],
    ),
)
@extend_schema(tags=["Product Images"])
class ProductImageViewSet(BaseViewSet):
    """
    ViewSet for managing product images.

    Provides CRUD operations for product images with proper
    ordering and primary image management.
    """

    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends: ClassVar[list] = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields: ClassVar[list[str]] = ["product", "is_primary"]
    ordering_fields: ClassVar[list[str]] = ["sort_order", "created_at"]
    ordering: ClassVar[list[str]] = ["sort_order", "created_at"]

    def get_queryset(self) -> QuerySet[ProductImage]:
        """Optimize queryset with product prefetching."""
        return super().get_queryset().select_related("product")

    @extend_schema(
        summary="Set as primary image",
        description="Set this image as the primary image for the product.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "image_id": {"type": "integer"},
                    "product_id": {"type": "integer"},
                },
            },
            400: OpenApiResponse(description="Invalid request"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Image not found"),
        },
        tags=["Product Images"],
    )
    @action(detail=True, methods=["post"], url_path="set-primary")
    def set_primary(self, request, pk=None):
        """Set image as primary for the product."""
        image = self.get_object()

        with transaction.atomic():
            # Remove primary status from other images
            ProductImage.objects.filter(
                product=image.product,
                is_primary=True,
            ).exclude(id=image.id).update(is_primary=False)

            # Set this image as primary
            image.is_primary = True
            image.save(update_fields=["is_primary", "updated_at"])

            # Log the change
            logger.info(
                "product_primary_image_changed",
                product_id=image.product.id,
                image_id=image.id,
                user_id=request.user.id,
            )

        return Response(
            {
                "message": "Image set as primary successfully",
                "image_id": image.id,
                "product_id": image.product.id,
            }
        )


@extend_schema_view(
    list=extend_schema(
        summary="List product specifications",
        description="Retrieve all specifications for products.",
        tags=["Product Specifications"],
    ),
    retrieve=extend_schema(
        summary="Get product specification",
        description="Retrieve a specific product specification.",
        tags=["Product Specifications"],
    ),
    create=extend_schema(
        summary="Add product specification",
        description="Add a new specification to a product.",
        tags=["Product Specifications"],
    ),
    update=extend_schema(
        summary="Update product specification",
        description="Update product specification details.",
        tags=["Product Specifications"],
    ),
    destroy=extend_schema(
        summary="Delete product specification",
        description="Remove a specification from a product.",
        tags=["Product Specifications"],
    ),
)
@extend_schema(tags=["Product Specifications"])
class ProductSpecificationViewSet(BaseViewSet):
    """
    ViewSet for managing product specifications.

    Provides CRUD operations for product specifications with
    proper validation and ordering.
    """

    queryset = ProductSpecification.objects.all()
    serializer_class = ProductSpecificationSerializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]
    filter_backends: ClassVar[list] = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields: ClassVar[list[str]] = ["product", "name"]
    ordering_fields: ClassVar[list[str]] = ["sort_order", "name", "created_at"]
    ordering: ClassVar[list[str]] = ["sort_order", "name"]

    def get_queryset(self) -> QuerySet[ProductSpecification]:
        """Optimize queryset with product prefetching."""
        return super().get_queryset().select_related("product")


# Read-only ViewSets for public API
@extend_schema_view(
    list=extend_schema(
        summary="Browse categories (Public)",
        description="Public endpoint for browsing product categories.",
        tags=["Public API"],
    ),
    retrieve=extend_schema(
        summary="View category (Public)",
        description="Public endpoint for viewing category details.",
        tags=["Public API"],
    ),
)
@extend_schema(tags=["Public API"])
class PublicCategoryViewSet(BaseReadOnlyViewSet):
    """
    Public read-only ViewSet for categories.

    Allows anonymous users to browse categories without authentication.
    """

    queryset = Category.objects.all()
    serializer_class = CategoryListSerializer
    permission_classes: ClassVar[list] = [permissions.AllowAny]
    filter_backends: ClassVar[list] = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields: ClassVar[list[str]] = ["parent", "is_featured"]
    search_fields: ClassVar[list[str]] = ["name", "description"]
    ordering: ClassVar[list[str]] = ["sort_order", "name"]

    def get_queryset(self) -> QuerySet[Category]:
        """Return only active categories for public access."""
        return super().get_queryset().filter(is_active=True)

    def get_serializer_class(self):
        """Use appropriate serializer for public access."""
        if self.action == "retrieve":
            return CategoryDetailSerializer
        return CategoryListSerializer

    @action(detail=False, methods=["get"])
    def roots(self, request) -> Response:
        """Get all root categories (categories without parent)."""
        queryset = self.get_queryset().filter(parent__isnull=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None) -> Response:
        """Get all direct children of a category."""
        category = self.get_object()
        queryset = self.get_queryset().filter(parent=category)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Browse products (Public)",
        description="Public endpoint for browsing products.",
        tags=["Public API"],
    ),
    retrieve=extend_schema(
        summary="View product (Public)",
        description="Public endpoint for viewing product details.",
        tags=["Public API"],
    ),
)
@extend_schema(tags=["Public API"])
class PublicProductViewSet(BaseReadOnlyViewSet):
    """
    Public read-only ViewSet for products.

    Allows anonymous users to browse products without authentication.
    """

    queryset = Product.objects.all()
    serializer_class = ProductListSerializer
    permission_classes: ClassVar[list] = [permissions.AllowAny]
    filterset_class = ProductFilter
    filter_backends: ClassVar[list] = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields: ClassVar[list[str]] = [
        "name",
        "description",
        "short_description",
        "sku",
    ]
    ordering_fields: ClassVar[list[str]] = ["name", "price", "created_at"]
    ordering: ClassVar[list[str]] = ["-created_at"]
    pagination_class = LargeResultsSetPagination

    def get_queryset(self) -> QuerySet[Product]:
        """Return only active products for public access."""
        queryset = super().get_queryset().filter(is_active=True)

        # Apply availability filters
        now = timezone.now()
        queryset = queryset.filter(
            Q(available_from__isnull=True) | Q(available_from__lte=now),
            Q(available_until__isnull=True) | Q(available_until__gte=now),
        )

        # Optimize based on action
        if self.action == "list":
            return queryset.select_related("category")
        if self.action == "retrieve":
            return queryset.select_related("category").prefetch_related(
                Prefetch(
                    "images",
                    queryset=ProductImage.objects.filter(is_active=True).order_by(
                        "sort_order",
                    ),
                ),
                Prefetch(
                    "specifications",
                    queryset=ProductSpecification.objects.filter(
                        is_active=True,
                    ).order_by("sort_order"),
                ),
            )

        return queryset

    def get_serializer_class(self):
        """Use appropriate serializer for public access."""
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    @extend_schema(
        summary="Get featured products (Public)",
        description="Public endpoint for browsing featured products.",
        responses={200: ProductListSerializer(many=True)},
        tags=["Public API"],
    )
    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Get featured products for public access."""
        queryset = self.get_queryset().filter(is_featured=True)
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Search products (Public)",
        description="Public endpoint for searching products.",
        parameters=[
            OpenApiParameter(
                name="q",
                description="Search query",
                required=True,
                type=str,
            ),
        ],
        responses={200: ProductListSerializer(many=True)},
        tags=["Public API"],
    )
    @action(detail=False, methods=["get"])
    def search(self, request):
        """Public product search."""
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"error": "Search query is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset()

        # Apply text search
        search_query = (
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(short_description__icontains=query)
            | Q(category__name__icontains=query)
        )
        queryset = queryset.filter(search_query).distinct()

        # Order by relevance (featured first, then by name)
        queryset = queryset.order_by("-is_featured", "name")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List product reviews",
        description="Retrieve a paginated list of product reviews with optional filtering by rating.",
        parameters=[
            OpenApiParameter(
                name="rating",
                description="Filter by rating (1-5)",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="product",
                description="Filter reviews by product ID",
                required=False,
                type=OpenApiTypes.INT,
            ),
        ],
        responses={
            200: ProductReviewSerializer(many=True),
            400: OpenApiResponse(description="Invalid filter parameters"),
        },
        tags=["Product Reviews"],
    ),
    retrieve=extend_schema(
        summary="Retrieve product review",
        description="Get detailed information about a specific product review.",
        responses={
            200: ProductReviewSerializer,
            404: OpenApiResponse(description="Review not found"),
        },
        tags=["Product Reviews"],
    ),
    create=extend_schema(
        summary="Create product review",
        description="Create a new review for a product. The product ID is taken from the URL.",
        request=ProductReviewSerializer,
        responses={
            201: ProductReviewSerializer,
            400: OpenApiResponse(description="Invalid input or duplicate review"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Product not found"),
        },
        tags=["Product Reviews"],
    ),
    update=extend_schema(
        summary="Update product review",
        description="Update an existing product review (only by owner).",
        request=ProductReviewSerializer,
        responses={
            200: ProductReviewSerializer,
            400: OpenApiResponse(description="Invalid input"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the review owner"),
            404: OpenApiResponse(description="Review not found"),
        },
        tags=["Product Reviews"],
    ),
    partial_update=extend_schema(
        summary="Partial update product review",
        description="Partially update an existing product review (only by owner).",
        request=ProductReviewSerializer,
        responses={
            200: ProductReviewSerializer,
            400: OpenApiResponse(description="Invalid input"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the review owner"),
            404: OpenApiResponse(description="Review not found"),
        },
        tags=["Product Reviews"],
    ),
    destroy=extend_schema(
        summary="Delete product review",
        description="Delete a product review (only by owner or admin).",
        responses={
            204: OpenApiResponse(description="Review deleted successfully"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the review owner or admin"),
            404: OpenApiResponse(description="Review not found"),
        },
        tags=["Product Reviews"],
    ),
)
@extend_schema(tags=["Product Reviews"])
class ProductReviewViewSet(BaseViewSet):
    """
    ViewSet for managing product reviews.
    """

    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["rating"]

    def get_queryset(self) -> QuerySet[ProductReview]:
        """
        Filter reviews for a specific product from the URL.
        """

        return super().get_queryset().filter(product_id=self.kwargs["product_pk"])

    def perform_create(self, serializer):
        """
        Associate the review with the product from the URL and the current user.
        """

        product = Product.objects.get(pk=self.kwargs["product_pk"])
        # Prevent duplicate reviews
        if ProductReview.objects.filter(
            product=product, user=self.request.user
        ).exists():
            raise serializers.ValidationError("You have already reviewed this product.")
        serializer.save(user=self.request.user, product=product)
