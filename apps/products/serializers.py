# apps/products/serializers.py

"""
Serializers for the products app.

Provides comprehensive serialization for products, categories, and related models
with proper validation, security, and performance optimization.
"""

from decimal import Decimal
from typing import Any, ClassVar

from django.utils.text import slugify
from rest_framework import serializers

from apps.core.serializers import (BaseModelSerializer, SanitizedCharField,
                                   SanitizedTextField)
from apps.products.models import (Category, Product, ProductImage,
                                  ProductSpecification)


class CategoryListSerializer(BaseModelSerializer):
    """
    Lightweight serializer for category listings.
    Optimized for performance in list views.
    """

    children_count = serializers.SerializerMethodField()
    product_count = serializers.ReadOnlyField()

    class Meta(BaseModelSerializer.Meta):
        model = Category
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "name",
            "slug",
            "description",
            "image",
            "icon",
            "sort_order",
            "is_featured",
            "children_count",
            "product_count",
        ]

    def get_children_count(self, obj: Category) -> int:
        """Get count of active child categories."""
        return obj.children.filter(is_active=True).count()


class CategoryDetailSerializer(BaseModelSerializer):
    """
    Detailed serializer for individual category views.
    Includes hierarchical information and nested children.
    """

    parent = CategoryListSerializer(read_only=True)
    children = CategoryListSerializer(many=True, read_only=True)
    ancestors = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    total_product_count = serializers.ReadOnlyField()
    breadcrumb = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Category
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "name",
            "slug",
            "description",
            "parent",
            "image",
            "icon",
            "sort_order",
            "is_featured",
            "meta_title",
            "meta_description",
            "meta_keywords",
            "children",
            "ancestors",
            "level",
            "total_product_count",
            "breadcrumb",
        ]

    def get_ancestors(self, obj: Category) -> list[dict]:
        """Get serialized ancestor categories."""
        ancestors = obj.get_ancestors()
        return CategoryListSerializer(ancestors, many=True).data

    def get_level(self, obj: Category) -> int:
        """Get category hierarchy level."""
        return obj.get_level()

    def get_breadcrumb(self, obj: Category) -> list[dict]:
        """Generate breadcrumb navigation data."""
        breadcrumb = []
        ancestors = obj.get_ancestors()

        for ancestor in ancestors:
            breadcrumb.append(
                {
                    "id": ancestor.id,
                    "name": ancestor.name,
                    "slug": ancestor.slug,
                },
            )

        # Add current category
        breadcrumb.append(
            {
                "id": obj.id,
                "name": obj.name,
                "slug": obj.slug,
            },
        )

        return breadcrumb


class CategoryCreateUpdateSerializer(BaseModelSerializer):
    """
    Serializer for creating and updating categories.
    Includes comprehensive validation and auto-slug generation.
    """

    name = SanitizedCharField(max_length=255)
    description = SanitizedTextField(required=False, allow_blank=True)
    meta_title = SanitizedCharField(max_length=255, required=False, allow_blank=True)
    meta_description = SanitizedTextField(
        max_length=500,
        required=False,
        allow_blank=True,
    )
    meta_keywords = SanitizedCharField(max_length=255, required=False, allow_blank=True)

    class Meta(BaseModelSerializer.Meta):
        model = Category
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "name",
            "slug",
            "description",
            "parent",
            "image",
            "icon",
            "sort_order",
            "is_featured",
            "meta_title",
            "meta_description",
            "meta_keywords",
        ]
        read_only_fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.read_only_fields,
            "slug",
        ]

    def validate_parent(self, value: Category | None) -> Category | None:
        """Validate parent category to prevent circular references."""
        if not value:
            return value

        # Check if parent is active
        if not value.is_active:
            error_msg = "Parent category must be active."
            raise serializers.ValidationError(error_msg)

        # During update, check for circular references
        if self.instance:
            current = value
            while current:
                if current.id == self.instance.id:
                    error_msg = (
                        "Cannot set parent that would create circular reference."
                    )
                    raise serializers.ValidationError(error_msg)
                current = current.parent

        return value

    def validate_sort_order(self, value: int) -> int:
        """Ensure sort_order is non-negative."""
        error_msg = "Sort order must be non-negative."
        if value < 0:
            raise serializers.ValidationError(error_msg)
        return value

    def create(self, validated_data: dict[str, Any]) -> Category:
        """Create category with auto-generated slug."""
        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data["name"])

        return super().create(validated_data)

    def update(self, instance: Category, validated_data: dict[str, Any]) -> Category:
        """Update category with slug regeneration if name changes."""
        if "name" in validated_data and validated_data["name"] != instance.name:
            validated_data["slug"] = slugify(validated_data["name"])

        return super().update(instance, validated_data)


class ProductImageSerializer(BaseModelSerializer):
    """
    Serializer for product images.
    """

    alt_text = SanitizedCharField(max_length=255, required=False, allow_blank=True)

    class Meta(BaseModelSerializer.Meta):
        model = ProductImage
        fields: ClassVar = [
            *BaseModelSerializer.Meta.fields,
            "image",
            "alt_text",
            "sort_order",
            "is_primary",
        ]

    def validate_sort_order(self, value: int) -> int:
        """Ensure sort_order is non-negative."""
        error_msg = "Sort order must be non-negative."
        if value < 0:
            raise serializers.ValidationError(error_msg)
        return value


class ProductSpecificationSerializer(BaseModelSerializer):
    """
    Serializer for product specifications.
    """

    name = SanitizedCharField(max_length=255)
    value = SanitizedTextField()

    class Meta(BaseModelSerializer.Meta):
        model = ProductSpecification
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "name",
            "value",
            "sort_order",
        ]

    def validate_sort_order(self, value: int) -> int:
        """Ensure sort_order is non-negative."""
        error_msg = "Sort order must be non-negative."
        if value < 0:
            raise serializers.ValidationError(error_msg)
        return value


class ProductListSerializer(BaseModelSerializer):
    """
    Lightweight serializer for product listings.
    Optimized for performance in list views and search results.
    """

    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    images_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Product
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "name",
            "slug",
            "sku",
            "short_description",
            "price",
            "compare_at_price",
            "featured_image",
            "category_name",
            "category_slug",
            "stock_quantity",
            "is_featured",
            "is_digital",
            "is_in_stock",
            "is_low_stock",
            "discount_percentage",
            "images_count",
        ]

    def get_images_count(self, obj: Product) -> int:
        """Get count of product images."""
        return obj.images.filter(is_active=True).count()


class ProductDetailSerializer(BaseModelSerializer):
    """
    Comprehensive serializer for detailed product views.
    Includes all related data and computed fields.
    """

    category = CategoryListSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)

    # Computed fields
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()

    # Category breadcrumb
    category_breadcrumb = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Product
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "name",
            "slug",
            "sku",
            "description",
            "short_description",
            "category",
            "price",
            "compare_at_price",
            "cost_price",
            "stock_quantity",
            "low_stock_threshold",
            "track_inventory",
            "allow_backorders",
            "weight",
            "dimensions_length",
            "dimensions_width",
            "dimensions_height",
            "featured_image",
            "is_featured",
            "is_digital",
            "requires_shipping",
            "meta_title",
            "meta_description",
            "meta_keywords",
            "available_from",
            "available_until",
            "images",
            "specifications",
            "is_in_stock",
            "is_low_stock",
            "discount_percentage",
            "profit_margin",
            "category_breadcrumb",
        ]

    def get_category_breadcrumb(self, obj: Product) -> list[dict]:
        """Generate category breadcrumb for the product."""
        if not obj.category:
            return []

        breadcrumb = []
        ancestors = obj.category.get_ancestors()

        for ancestor in ancestors:
            breadcrumb.append(
                {
                    "id": ancestor.id,
                    "name": ancestor.name,
                    "slug": ancestor.slug,
                },
            )

        # Add product's category
        breadcrumb.append(
            {
                "id": obj.category.id,
                "name": obj.category.name,
                "slug": obj.category.slug,
            },
        )

        return breadcrumb


class ProductCreateUpdateSerializer(BaseModelSerializer):
    """
    Serializer for creating and updating products.
    Includes comprehensive validation and business logic.
    """

    # Error messages
    ERROR_SKU_EXISTS = "Product with this SKU already exists."
    ERROR_PRICE_ZERO = "Price must be greater than zero."
    ERROR_COMPARE_PRICE_ZERO = "Compare at price must be greater than zero."
    ERROR_COST_PRICE_NEGATIVE = "Cost price cannot be negative."
    ERROR_STOCK_QUANTITY_NEGATIVE = "Stock quantity cannot be negative."
    ERROR_LOW_STOCK_THRESHOLD_NEGATIVE = "Low stock threshold cannot be negative."
    ERROR_WEIGHT_INVALID = "Weight must be greater than zero."
    ERROR_LENGTH_INVALID = "Length must be greater than zero."
    ERROR_WIDTH_INVALID = "Width must be greater than zero."
    ERROR_HEIGHT_INVALID = "Height must be greater than zero."
    ERROR_CATEGORY_INACTIVE = "Selected category must be active."

    name = SanitizedCharField(max_length=255)
    description = SanitizedTextField()
    short_description = SanitizedTextField(
        max_length=500,
        required=False,
        allow_blank=True,
    )
    meta_title = SanitizedCharField(max_length=255, required=False, allow_blank=True)
    meta_description = SanitizedTextField(
        max_length=500,
        required=False,
        allow_blank=True,
    )
    meta_keywords = SanitizedCharField(max_length=255, required=False, allow_blank=True)

    # Nested serializers for creation/update
    images = ProductImageSerializer(many=True, required=False)
    specifications = ProductSpecificationSerializer(many=True, required=False)

    class Meta(BaseModelSerializer.Meta):
        model = Product
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "name",
            "slug",
            "sku",
            "description",
            "short_description",
            "category",
            "price",
            "compare_at_price",
            "cost_price",
            "stock_quantity",
            "low_stock_threshold",
            "track_inventory",
            "allow_backorders",
            "weight",
            "dimensions_length",
            "dimensions_width",
            "dimensions_height",
            "featured_image",
            "is_featured",
            "is_digital",
            "requires_shipping",
            "meta_title",
            "meta_description",
            "meta_keywords",
            "available_from",
            "available_until",
            "images",
            "specifications",
        ]
        read_only_fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.read_only_fields,
            "slug",
        ]

    def validate_sku(self, value: str) -> str:
        """Validate SKU uniqueness and format."""
        value = value.strip().upper()

        # Check uniqueness
        queryset = Product.all_objects.all()
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.filter(sku=value).exists():
            raise serializers.ValidationError(self.ERROR_SKU_EXISTS)

        return value

    def validate_price(self, value: Decimal) -> Decimal:
        """Validate product price."""
        if value <= 0:
            raise serializers.ValidationError(self.ERROR_PRICE_ZERO)
        return value

    def validate_compare_at_price(self, value: Decimal | None) -> Decimal | None:
        """Validate compare at price."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(self.ERROR_COMPARE_PRICE_ZERO)
        return value

    def validate_cost_price(self, value: Decimal | None) -> Decimal | None:
        """Validate cost price."""
        if value is not None and value < 0:
            raise serializers.ValidationError(self.ERROR_COST_PRICE_NEGATIVE)
        return value

    def validate_stock_quantity(self, value: int) -> int:
        """Validate stock quantity."""
        if value < 0:
            raise serializers.ValidationError(self.ERROR_STOCK_QUANTITY_NEGATIVE)
        return value

    def validate_low_stock_threshold(self, value: int) -> int:
        """Validate low stock threshold."""
        if value < 0:
            raise serializers.ValidationError(self.ERROR_LOW_STOCK_THRESHOLD_NEGATIVE)
        return value

    def validate_weight(self, value: Decimal | None) -> Decimal | None:
        """Validate product weight."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(self.ERROR_WEIGHT_INVALID)
        return value

    def validate_dimensions_length(self, value: Decimal | None) -> Decimal | None:
        """Validate product length."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(self.ERROR_LENGTH_INVALID)
        return value

    def validate_dimensions_width(self, value: Decimal | None) -> Decimal | None:
        """Validate product width."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(self.ERROR_WIDTH_INVALID)
        return value

    def validate_dimensions_height(self, value: Decimal | None) -> Decimal | None:
        """Validate product height."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(self.ERROR_HEIGHT_INVALID)
        return value

    def validate_category(self, value: Category) -> Category:
        """Validate category is active."""
        if not value.is_active:
            raise serializers.ValidationError(self.ERROR_CATEGORY_INACTIVE)
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation."""
        attrs = super().validate(attrs)

        # Validate compare_at_price vs price
        price = attrs.get("price", self.instance.price if self.instance else None)
        compare_at_price = attrs.get("compare_at_price")

        if compare_at_price and price and compare_at_price <= price:
            raise serializers.ValidationError(
                {
                    "compare_at_price": "Compare at price must be higher than the regular price.",
                },
            )

        # Validate availability dates
        available_from = attrs.get("available_from")
        available_until = attrs.get("available_until")

        if available_from and available_until and available_from >= available_until:
            raise serializers.ValidationError(
                {
                    "available_until": "Available until date must be after available from date.",
                },
            )

        # Validate digital product settings
        is_digital = attrs.get(
            "is_digital",
            self.instance.is_digital if self.instance else False,
        )
        requires_shipping = attrs.get(
            "requires_shipping",
            self.instance.requires_shipping if self.instance else True,
        )

        if is_digital and requires_shipping:
            attrs["requires_shipping"] = False  # Auto-correct for digital products

        return attrs

    def create(self, validated_data: dict[str, Any]) -> Product:
        """Create product with related objects."""
        images_data = validated_data.pop("images", [])
        specifications_data = validated_data.pop("specifications", [])

        # Auto-generate slug if not provided
        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data["name"])

        # Create the product
        product = super().create(validated_data)

        # Create related images
        for image_data in images_data:
            ProductImage.objects.create(product=product, **image_data)

        # Create related specifications
        for spec_data in specifications_data:
            ProductSpecification.objects.create(product=product, **spec_data)

        return product

    def update(self, instance: Product, validated_data: dict[str, Any]) -> Product:
        """Update product with related objects."""
        images_data = validated_data.pop("images", None)
        specifications_data = validated_data.pop("specifications", None)

        # Update slug if name changes
        if "name" in validated_data and validated_data["name"] != instance.name:
            validated_data["slug"] = slugify(validated_data["name"])

        # Update the product
        product = super().update(instance, validated_data)

        # Update images if provided
        if images_data is not None:
            # Remove existing images
            product.images.all().delete()

            # Create new images
            for image_data in images_data:
                ProductImage.objects.create(product=product, **image_data)

        # Update specifications if provided
        if specifications_data is not None:
            # Remove existing specifications
            product.specifications.all().delete()

            # Create new specifications
            for spec_data in specifications_data:
                ProductSpecification.objects.create(product=product, **spec_data)

        return product


class ProductInventorySerializer(BaseModelSerializer):
    """
    Specialized serializer for inventory management.
    Used for stock updates and inventory tracking.
    """

    # Error messages
    ERROR_STOCK_QUANTITY_NEGATIVE = "Stock quantity cannot be negative."
    ERROR_LOW_STOCK_THRESHOLD_NEGATIVE = "Low stock threshold cannot be negative."

    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()

    class Meta(BaseModelSerializer.Meta):
        model = Product
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "name",
            "sku",
            "stock_quantity",
            "low_stock_threshold",
            "track_inventory",
            "allow_backorders",
            "is_in_stock",
            "is_low_stock",
        ]
        read_only_fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.read_only_fields,
            "name",
            "sku",
        ]

    def validate_stock_quantity(self, value: int) -> int:
        """Validate stock quantity for inventory updates."""
        if value < 0:
            raise serializers.ValidationError(self.ERROR_STOCK_QUANTITY_NEGATIVE)
        return value

    def validate_low_stock_threshold(self, value: int) -> int:
        """Validate low stock threshold."""
        if value < 0:
            raise serializers.ValidationError(self.ERROR_LOW_STOCK_THRESHOLD_NEGATIVE)
        return value


class ProductPricingSerializer(BaseModelSerializer):
    """
    Specialized serializer for pricing management.
    Used for price updates and margin calculations.
    """

    # Error messages
    ERROR_PRICE_ZERO = "Price must be greater than zero."
    ERROR_COMPARE_PRICE_ZERO = "Compare at price must be greater than zero."
    ERROR_COST_PRICE_NEGATIVE = "Cost price cannot be negative."
    ERROR_INVALID_PRICE_COMPARISON = "Compare at price must be greater than price."
    ERROR_INVALID_COST_PRICE = "Cost price cannot be greater than price."

    discount_percentage = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()

    class Meta(BaseModelSerializer.Meta):
        """Meta options for ProductPricingSerializer."""

        model = Product
        fields: ClassVar[list] = [
            *BaseModelSerializer.Meta.fields,
            "price",
            "compare_at_price",
            "cost_price",
            "discount_percentage",
            "profit_margin",
        ]
        read_only_fields: ClassVar = [
            *BaseModelSerializer.Meta.read_only_fields,
            "name",
            "sku",
        ]

    def validate_price(self, value: Decimal) -> Decimal:
        """Validate product price."""
        if value <= 0:
            raise serializers.ValidationError(self.ERROR_PRICE_ZERO)
        return value

    def validate_compare_at_price(self, value: Decimal | None) -> Decimal | None:
        """Validate compare at price."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(self.ERROR_COMPARE_PRICE_ZERO)
        return value

    def validate_cost_price(self, value: Decimal | None) -> Decimal | None:
        """Validate cost price."""
        if value is not None and value < 0:
            raise serializers.ValidationError(self.ERROR_COST_PRICE_NEGATIVE)
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation for pricing."""
        price = attrs.get("price", getattr(self.instance, "price", None))
        compare_at_price = attrs.get(
            "compare_at_price",
            getattr(self.instance, "compare_at_price", None),
        )
        cost_price = attrs.get("cost_price", getattr(self.instance, "cost_price", None))

        if compare_at_price is not None and price and compare_at_price <= price:
            raise serializers.ValidationError(
                {"compare_at_price": self.ERROR_INVALID_PRICE_COMPARISON},
            )

        if cost_price is not None and price and cost_price > price:
            raise serializers.ValidationError(
                {"cost_price": self.ERROR_INVALID_COST_PRICE},
            )

        return attrs


# Serializer selector utility
class ProductSerializerSelector:
    """
    Utility class for selecting appropriate serializers based on context.
    """

    @staticmethod
    def get_serializer_class(request=None, action=None, context=None):
        """
        Get the appropriate serializer class based on action and context.
        """
        if action == "list":
            return ProductListSerializer
        if action == "retrieve":
            return ProductDetailSerializer
        if action in ["create", "update", "partial_update"]:
            return ProductCreateUpdateSerializer
        if action == "inventory":
            return ProductInventorySerializer
        if action == "pricing":
            return ProductPricingSerializer
        return ProductDetailSerializer


class CategorySerializerSelector:
    """
    Utility class for selecting appropriate category serializers.
    """

    @staticmethod
    def get_serializer_class(request=None, action=None, context=None):
        """
        Get the appropriate serializer class based on action and context.
        """
        if action == "list":
            return CategoryListSerializer
        if action == "retrieve":
            return CategoryDetailSerializer
        if action in ["create", "update", "partial_update"]:
            return CategoryCreateUpdateSerializer
        return CategoryDetailSerializer
