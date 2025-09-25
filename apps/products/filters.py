# apps/products/filters.py

"""
Django filters for the products app.

Provides advanced filtering capabilities for products and categories
with proper validation and performance optimization.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

import django_filters
import structlog
from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.products.models import Category, Product

logger = structlog.get_logger(__name__)


class CategoryFilter(django_filters.FilterSet):
    """
    FilterSet for Category model with hierarchical and feature filters.
    """

    # Hierarchical filters
    parent = django_filters.UUIDFilter(
        field_name="parent__id",
        help_text="Filter by parent category ID",
    )

    parent_isnull = django_filters.BooleanFilter(
        field_name="parent",
        lookup_expr="isnull",
        help_text="Filter for root categories (true) or child categories (false)",
    )

    level = django_filters.NumberFilter(
        method="filter_by_level",
        help_text="Filter by hierarchy level (0=root, 1=first level children, etc.)",
    )

    # Feature filters
    is_featured = django_filters.BooleanFilter(
        help_text="Filter by featured status",
    )

    has_products = django_filters.BooleanFilter(
        method="filter_has_products",
        help_text="Filter categories that have products",
    )

    has_children = django_filters.BooleanFilter(
        method="filter_has_children",
        help_text="Filter categories that have child categories",
    )

    # Text search
    name_contains = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
        help_text="Filter by name containing text",
    )

    # Date range filters
    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        help_text="Filter categories created after this date",
    )

    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        help_text="Filter categories created before this date",
    )

    class Meta:
        model = Category
        fields: ClassVar[list] = [
            "is_active",
            "is_featured",
            "parent",
            "parent_isnull",
            "name_contains",
            "has_products",
            "has_children",
            "level",
            "created_after",
            "created_before",
        ]

    def filter_by_level(
        self,
        queryset: QuerySet[Category],
        name: str,
        value: int,
    ) -> QuerySet[Category]:
        """Filter categories by hierarchy level."""
        if value is None:
            return queryset

        if value < 0:
            return queryset.none()

        if value == 0:
            # Root categories
            return queryset.filter(parent__isnull=True)

        # Build filter for specific level
        filter_conditions = Q()
        current_field = "parent"

        # Build the chain: parent__parent__parent... (value times)
        for i in range(value):
            if i == value - 1:
                # Last level should not be null
                filter_conditions &= Q(**{f"{current_field}__isnull": False})
            else:
                # Intermediate levels should exist
                filter_conditions &= Q(**{f"{current_field}__isnull": False})
                current_field += "__parent"

        # The level above should be null (to ensure exact level)
        next_level_field = current_field + "__parent"
        filter_conditions &= Q(**{f"{next_level_field}__isnull": True})

        return queryset.filter(filter_conditions)

    def filter_has_products(
        self,
        queryset: QuerySet[Category],
        name: str,
        value: bool,
    ) -> QuerySet[Category]:
        """Filter categories that have products."""
        if value is None:
            return queryset

        if value:
            return queryset.filter(products__is_active=True).distinct()
        return queryset.exclude(products__is_active=True).distinct()

    def filter_has_children(
        self,
        queryset: QuerySet[Category],
        name: str,
        value: bool,
    ) -> QuerySet[Category]:
        """Filter categories that have child categories."""
        if value is None:
            return queryset

        if value:
            return queryset.filter(children__is_active=True).distinct()
        return queryset.exclude(children__is_active=True).distinct()


PRICE_RANGE_PARTS_COUNT = 2


class ProductFilter(django_filters.FilterSet):
    """
    Advanced FilterSet for Product model with comprehensive filtering options.
    """

    # Category filters
    category = django_filters.UUIDFilter(
        field_name="category__id",
        help_text="Filter by category ID",
    )

    category_slug = django_filters.CharFilter(
        field_name="category__slug",
        help_text="Filter by category slug",
    )

    category_tree = django_filters.UUIDFilter(
        method="filter_category_tree",
        help_text="Filter by category and all its descendants",
    )

    # Price filters
    price = django_filters.RangeFilter(
        help_text="Filter by exact price range",
    )

    min_price = django_filters.NumberFilter(
        field_name="price__amount",
        lookup_expr="gte",
        help_text="Filter by minimum price",
    )

    max_price = django_filters.NumberFilter(
        field_name="price__amount",
        lookup_expr="lte",
        help_text="Filter by maximum price",
    )

    price_range = django_filters.CharFilter(
        method="filter_price_range",
        help_text="Filter by price range (format: 'min,max' or predefined ranges like 'budget', 'mid', 'premium')",
    )

    # Inventory filters
    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock",
        help_text="Filter products that are in stock",
    )

    low_stock = django_filters.BooleanFilter(
        method="filter_low_stock",
        help_text="Filter products with low stock",
    )

    stock_range = django_filters.RangeFilter(
        field_name="stock_quantity",
        help_text="Filter by stock quantity range",
    )

    track_inventory = django_filters.BooleanFilter(
        help_text="Filter products with inventory tracking enabled",
    )

    allow_backorders = django_filters.BooleanFilter(
        help_text="Filter products that allow backorders",
    )

    # Feature filters
    is_featured = django_filters.BooleanFilter(
        help_text="Filter featured products",
    )

    is_digital = django_filters.BooleanFilter(
        help_text="Filter digital products",
    )

    requires_shipping = django_filters.BooleanFilter(
        help_text="Filter products that require shipping",
    )

    # Discount filters
    on_sale = django_filters.BooleanFilter(
        method="filter_on_sale",
        help_text="Filter products that are on sale (have compare_at_price)",
    )

    discount_percentage = django_filters.RangeFilter(
        method="filter_discount_percentage",
        help_text="Filter by discount percentage range",
    )

    # Text search filters
    name_contains = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
        help_text="Filter by name containing text",
    )

    sku_contains = django_filters.CharFilter(
        field_name="sku",
        lookup_expr="icontains",
        help_text="Filter by SKU containing text",
    )

    description_contains = django_filters.CharFilter(
        field_name="description",
        lookup_expr="icontains",
        help_text="Filter by description containing text",
    )

    # Availability filters
    available_now = django_filters.BooleanFilter(
        method="filter_available_now",
        help_text="Filter products available right now",
    )

    available_from = django_filters.DateTimeFilter(
        field_name="available_from",
        lookup_expr="gte",
        help_text="Filter products available from this date",
    )

    available_until = django_filters.DateTimeFilter(
        field_name="available_until",
        lookup_expr="lte",
        help_text="Filter products available until this date",
    )

    # Physical properties filters
    weight_range = django_filters.RangeFilter(
        field_name="weight",
        help_text="Filter by weight range (kg)",
    )

    has_dimensions = django_filters.BooleanFilter(
        method="filter_has_dimensions",
        help_text="Filter products that have dimensions specified",
    )

    # Date filters
    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        help_text="Filter products created after this date",
    )

    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        help_text="Filter products created before this date",
    )

    updated_after = django_filters.DateTimeFilter(
        field_name="updated_at",
        lookup_expr="gte",
        help_text="Filter products updated after this date",
    )

    # Specification filters
    has_specifications = django_filters.BooleanFilter(
        method="filter_has_specifications",
        help_text="Filter products that have specifications",
    )

    specification = django_filters.CharFilter(
        method="filter_specification",
        help_text="Filter by specification (format: 'name:value')",
    )

    class Meta:
        model = Product
        fields: ClassVar[list] = [
            "is_active",
            "category",
            "category_slug",
            "category_tree",
            "price",
            "min_price",
            "max_price",
            "price_range",
            "in_stock",
            "low_stock",
            "stock_range",
            "track_inventory",
            "allow_backorders",
            "is_featured",
            "is_digital",
            "requires_shipping",
            "on_sale",
            "discount_percentage",
            "name_contains",
            "sku_contains",
            "description_contains",
            "available_now",
            "available_from",
            "available_until",
            "weight_range",
            "has_dimensions",
            "created_after",
            "created_before",
            "updated_after",
            "has_specifications",
            "specification",
        ]

    def filter_category_tree(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: str,
    ) -> QuerySet[Product]:
        """Filter products by category and all its descendant categories."""
        if not value:
            return queryset

        try:
            category = Category.objects.get(id=value, is_active=True)
        except Category.DoesNotExist:
            return queryset.none()

        # Get all descendant categories
        descendant_categories = category.get_descendants()
        category_ids = [category.id] + [cat.id for cat in descendant_categories]

        return queryset.filter(category__id__in=category_ids)

    def filter_price_range(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: str,
    ) -> QuerySet[Product]:
        """Filter products by price range with predefined ranges or custom range."""
        if not value:
            return queryset

        # Predefined ranges
        predefined_ranges = {
            "budget": (Decimal("0"), Decimal("50")),
            "mid": (Decimal("50"), Decimal("200")),
            "premium": (Decimal("200"), Decimal("1000")),
            "luxury": (Decimal("1000"), None),
        }

        if value.lower() in predefined_ranges:
            min_price, max_price = predefined_ranges[value.lower()]
            queryset = queryset.filter(price__amount__gte=min_price)
            if max_price:
                queryset = queryset.filter(price__amount__lte=max_price)
            return queryset

        # Custom range format: "min,max"
        try:
            parts = value.split(",")
            if len(parts) == PRICE_RANGE_PARTS_COUNT:
                min_price_str = parts[0].strip()
                max_price_str = parts[1].strip()

                min_price = Decimal(min_price_str) if min_price_str else None
                max_price = Decimal(max_price_str) if max_price_str else None

                if min_price is not None:
                    queryset = queryset.filter(price__amount__gte=min_price)
                if max_price is not None:
                    queryset = queryset.filter(price__amount__lte=max_price)
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.warning(f"Invalid price range format: {value}, error: {e}")
            # Return original queryset instead of failing

        return queryset

    def filter_in_stock(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: bool,
    ) -> QuerySet[Product]:
        """Filter products that are in stock."""
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                Q(track_inventory=False)
                | Q(track_inventory=True, stock_quantity__gt=0)
                | Q(track_inventory=True, allow_backorders=True),
            )
        return queryset.filter(
            track_inventory=True,
            stock_quantity=0,
            allow_backorders=False,
        )

    def filter_low_stock(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: bool,
    ) -> QuerySet[Product]:
        """Filter products with low stock."""
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                track_inventory=True,
                stock_quantity__lte=models.F("low_stock_threshold"),
                stock_quantity__gt=0,
            )
        return queryset.exclude(
            track_inventory=True,
            stock_quantity__lte=models.F("low_stock_threshold"),
            stock_quantity__gt=0,
        )

    def filter_on_sale(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: bool,
    ) -> QuerySet[Product]:
        """Filter products that are on sale."""
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                compare_at_price__isnull=False,
                compare_at_price__amount__gt=models.F("price__amount"),
            )
        return queryset.filter(
            Q(compare_at_price__isnull=True)
            | Q(compare_at_price__amount__lte=models.F("price__amount")),
        )

    def filter_discount_percentage(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: Any,
    ) -> QuerySet[Product]:
        """Filter products by discount percentage range."""
        if not value or not hasattr(value, "start") or not hasattr(value, "stop"):
            return queryset

        min_discount = value.start
        max_discount = value.stop

        if min_discount is None and max_discount is None:
            return queryset

        # Filter products with compare_at_price
        filtered_queryset = queryset.filter(
            compare_at_price__isnull=False,
            compare_at_price__amount__gt=models.F("price__amount"),
        )

        # Calculate discount percentage and filter
        # This is a simplified approach - for exact calculation, use raw SQL
        if min_discount is not None:
            filtered_queryset = filtered_queryset.annotate(
                max_price_for_min_discount=models.F("compare_at_price__amount")
                * (100 - min_discount)
                / 100,
            ).filter(price__amount__lte=models.F("max_price_for_min_discount"))

        if max_discount is not None:
            # Products with at most max_discount percentage
            filtered_queryset = filtered_queryset.annotate(
                min_price_for_max_discount=models.F("compare_at_price__amount")
                * (100 - max_discount)
                / 100,
            ).filter(price__amount__gte=models.F("min_price_for_max_discount"))

        return filtered_queryset

    def filter_available_now(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: bool,
    ) -> QuerySet[Product]:
        """Filter products available right now."""
        if value is None:
            return queryset

        now = timezone.now()

        if value:
            return queryset.filter(
                Q(available_from__isnull=True) | Q(available_from__lte=now),
                Q(available_until__isnull=True) | Q(available_until__gte=now),
            )
        return queryset.filter(
            Q(available_from__isnull=False, available_from__gt=now)
            | Q(available_until__isnull=False, available_until__lt=now),
        )

    def filter_has_dimensions(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: bool,
    ) -> QuerySet[Product]:
        """Filter products that have dimensions specified."""
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                dimensions_length__isnull=False,
                dimensions_width__isnull=False,
                dimensions_height__isnull=False,
            )
        return queryset.filter(
            Q(dimensions_length__isnull=True)
            | Q(dimensions_width__isnull=True)
            | Q(dimensions_height__isnull=True),
        )

    def filter_has_specifications(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: bool,
    ) -> QuerySet[Product]:
        """Filter products that have specifications."""
        if value is None:
            return queryset

        if value:
            return queryset.filter(specifications__is_active=True).distinct()
        return queryset.exclude(specifications__is_active=True).distinct()

    def filter_specification(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: str,
    ) -> QuerySet[Product]:
        """Filter products by specification name:value pair."""
        if not value:
            return queryset

        try:
            if ":" in value:
                spec_name, spec_value = value.split(":", 1)
                return queryset.filter(
                    specifications__name__iexact=spec_name.strip(),
                    specifications__value__icontains=spec_value.strip(),
                    specifications__is_active=True,
                ).distinct()
            # Search in both name and value
            return queryset.filter(
                Q(specifications__name__icontains=value)
                | Q(specifications__value__icontains=value),
                specifications__is_active=True,
            ).distinct()
        except Exception:
            return queryset


class PriceRangeFilter(django_filters.Filter):
    """
    Custom filter for price ranges with better validation and error handling.
    """

    def filter(self, qs: QuerySet, value: str) -> QuerySet:
        """Filter queryset by price range."""
        if not value:
            return qs

        if self._is_predefined_range(value):
            return self._filter_predefined_range(qs, value)

        if self._is_custom_range(value):
            return self._filter_custom_range(qs, value)

        return qs

    def _is_predefined_range(self, value: str) -> bool:
        predefined_ranges = {
            "under-25",
            "25-50",
            "50-100",
            "100-200",
            "200-500",
            "over-500",
        }
        return value in predefined_ranges

    def _filter_predefined_range(self, qs: QuerySet, value: str) -> QuerySet:
        predefined_ranges = {
            "under-25": (None, Decimal("25")),
            "25-50": (Decimal("25"), Decimal("50")),
            "50-100": (Decimal("50"), Decimal("100")),
            "100-200": (Decimal("100"), Decimal("200")),
            "200-500": (Decimal("200"), Decimal("500")),
            "over-500": (Decimal("500"), None),
        }
        min_price, max_price = predefined_ranges[value]
        if min_price is not None:
            qs = qs.filter(price__amount__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__amount__lte=max_price)
        return qs

    def _is_custom_range(self, value: str) -> bool:
        return any(sep in value for sep in ["-", ",", ":"])

    def _filter_custom_range(self, qs: QuerySet, value: str) -> QuerySet:
        separators = ["-", ",", ":"]
        for sep in separators:
            if sep in value:
                parts = value.split(sep, 1)
                if len(parts) == 2:
                    min_str, max_str = parts
                    try:
                        if min_str.strip():
                            min_price = Decimal(min_str.strip())
                            qs = qs.filter(price__amount__gte=min_price)
                        if max_str.strip():
                            max_price = Decimal(max_str.strip())
                            qs = qs.filter(price__amount__lte=max_price)
                    except (InvalidOperation, ValueError, TypeError):
                        pass
                    break
        return qs


# Advanced search filter
class ProductSearchFilter(django_filters.CharFilter):
    """
    Advanced search filter that searches across multiple fields
    with relevance scoring and fuzzy matching.
    """

    def filter(self, qs: QuerySet, value: str) -> QuerySet:
        """
        Filter queryset with advanced search capabilities.
        """
        if not value:
            return qs

        search_terms = value.strip().split()
        if not search_terms:
            return qs

        # Build search query with OR conditions for each term
        search_query = Q()

        for term in search_terms:
            term_query = (
                Q(name__icontains=term)
                | Q(description__icontains=term)
                | Q(short_description__icontains=term)
                | Q(sku__iexact=term)
                | Q(category__name__icontains=term)
                | Q(specifications__name__icontains=term)
                | Q(specifications__value__icontains=term)
            )
            search_query |= term_query

        # Apply the search filter
        qs = qs.filter(search_query).distinct()

        # Add relevance ordering (featured products first, then by name)
        qs = qs.order_by("-is_featured", "name")

        return qs


# Utility functions for common filter operations
def get_category_descendants(category_id: str) -> list[str]:
    """
    Get all descendant category IDs for a given category.
    Returns a list of category IDs including the original.
    """
    try:
        category = Category.objects.get(id=category_id, is_active=True)
        descendants = category.get_descendants()
        return [str(category.id)] + [str(cat.id) for cat in descendants]
    except Category.DoesNotExist:
        return []


def build_price_filter(min_price: str | None, max_price: str | None) -> Q:
    """
    Build a price filter Q object with validation.
    """
    filter_q = Q()

    try:
        if min_price:
            min_val = Decimal(str(min_price))
            filter_q &= Q(price__amount__gte=min_val)
    except (InvalidOperation, ValueError):
        pass

    try:
        if max_price:
            max_val = Decimal(str(max_price))
            filter_q &= Q(price__amount__lte=max_val)
    except (InvalidOperation, ValueError):
        pass

    return filter_q


def build_availability_filter(available_now: bool = True) -> Q:
    """
    Build an availability filter Q object.
    """
    if not available_now:
        return Q()

    now = timezone.now()
    return Q(
        Q(available_from__isnull=True) | Q(available_from__lte=now),
        Q(available_until__isnull=True) | Q(available_until__gte=now),
    )


# Custom ordering filters
class ProductOrderingFilter(django_filters.OrderingFilter):
    """
    Custom ordering filter with additional options for products.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra["choices"] += [
            ("price", "Price: Low to High"),
            ("-price", "Price: High to Low"),
            ("name", "Name: A to Z"),
            ("-name", "Name: Z to A"),
            ("-created_at", "Newest First"),
            ("created_at", "Oldest First"),
            ("-is_featured", "Featured First"),
            ("stock_quantity", "Stock: Low to High"),
            ("-stock_quantity", "Stock: High to Low"),
            ("category__name", "Category: A to Z"),
            ("-category__name", "Category: Z to A"),
        ]

    def filter(self, qs: QuerySet, value: list) -> QuerySet:
        """
        Apply ordering with fallback for consistent results.
        """
        if value:
            # Apply the requested ordering
            qs = super().filter(qs, value)

            # Add fallback ordering for consistency
            ordering = qs.query.order_by
            if ordering and "id" not in [field.lstrip("-") for field in ordering]:
                # Add ID as final ordering field for consistent pagination
                qs = qs.order_by(*ordering, "id")

        return qs


# Filter combinations for common use cases
class FeaturedProductsFilter(django_filters.FilterSet):
    """
    Specialized filter for featured products page.
    """

    category = django_filters.UUIDFilter(field_name="category__id")
    price_range = PriceRangeFilter()
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields: ClassVar[list] = ["category", "price_range", "in_stock"]

    def filter_in_stock(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: bool,
    ) -> QuerySet[Product]:
        """Filter products that are in stock."""
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                Q(track_inventory=False)
                | Q(track_inventory=True, stock_quantity__gt=0)
                | Q(track_inventory=True, allow_backorders=True),
            )

        return queryset

    @property
    def qs(self):
        """Override to always filter for featured and active products."""
        parent_qs = super().qs
        return parent_qs.filter(is_featured=True, is_active=True)


class SearchResultsFilter(django_filters.FilterSet):
    """
    Specialized filter for search results page.
    """

    q = ProductSearchFilter()
    category = django_filters.UUIDFilter(field_name="category__id")
    price_range = PriceRangeFilter()
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields: ClassVar[list] = ["q", "category", "price_range", "in_stock"]

    def filter_in_stock(
        self,
        queryset: QuerySet[Product],
        name: str,
        value: bool,
    ) -> QuerySet[Product]:
        """Filter products that are in stock."""
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                Q(track_inventory=False)
                | Q(track_inventory=True, stock_quantity__gt=0)
                | Q(track_inventory=True, allow_backorders=True),
            )

        return queryset
