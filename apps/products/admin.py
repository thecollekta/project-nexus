# apps/products/admin.py

"""
Django admin configuration for the products app.

Provides comprehensive admin interface for managing products, categories,
images, and specifications with proper filtering and search capabilities.
"""

from typing import ClassVar

from django.contrib import admin
from django.utils.html import format_html

from apps.products.models import (Category, PriceHistory, Product,
                                  ProductImage, ProductReview,
                                  ProductSpecification)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Category model with hierarchical display.
    """

    list_display: ClassVar[list] = [
        "name",
        "parent",
        "level_display",
        "product_count_display",
        "is_featured",
        "is_active",
        "sort_order",
        "created_at",
    ]

    list_filter: ClassVar[list] = [
        "is_active",
        "is_featured",
        "parent",
        "created_at",
        "updated_at",
    ]

    search_fields: ClassVar[list] = [
        "name",
        "description",
        "meta_title",
        "meta_description",
    ]

    list_select_related: ClassVar[list] = ["parent"]
    readonly_fields: ClassVar[list] = [
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]
    prepopulated_fields: ClassVar[dict] = {"slug": ("name",)}
    ordering: ClassVar[list] = ["sort_order", "name"]

    def get_queryset(self, request):
        """Optimize queryset with annotations and select_related."""
        queryset = super().get_queryset(request)
        # No need to annotate since we'll use the model's product_count property
        return queryset.select_related("parent")

    def product_count_display(self, obj):
        """Display product count with link to filtered product list."""
        from django.urls import reverse  # noqa: PLC0415
        from django.utils.html import format_html  # noqa: PLC0415

        url = (
            reverse("admin:products_product_changelist")
            + f"?category__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.product_count)

    product_count_display.short_description = "Products"
    product_count_display.admin_order_field = (
        None  # Remove ordering by product count since it's a property
    )

    def level_display(self, obj):
        """Display category level in hierarchy."""
        level = 0
        current = obj.parent
        while current:
            level += 1
            current = current.parent
        return level

    level_display.short_description = "Level"

    def save_model(self, request, obj, form, change):
        """Set audit fields on save."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        """
        Override to filter parent categories to prevent circular references.
        """
        form = super().get_form(request, obj, **kwargs)
        if obj:
            # When editing an existing category, exclude itself and its descendants from parent choices
            form.base_fields["parent"].queryset = Category.objects.exclude(
                id__in=[obj.id] + [c.id for c in obj.get_descendants()],
            )
        return form


class ProductImageInline(admin.TabularInline):
    """
    Inline admin for product images.
    """

    model = ProductImage
    extra = 0
    min_num = 0
    fields: ClassVar[list] = [
        "image",
        "alt_text",
        "sort_order",
        "is_primary",
        "is_active",
    ]
    readonly_fields: ClassVar[list] = ["created_at", "updated_at"]


class ProductSpecificationInline(admin.TabularInline):
    """
    Inline admin for product specifications.
    """

    model = ProductSpecification
    extra = 0
    min_num = 0
    fields: ClassVar[list] = ["name", "value", "sort_order", "is_active"]
    readonly_fields: ClassVar[list] = ["created_at", "updated_at"]


class ProductReviewInline(admin.TabularInline):
    """
    Inline admin for product reviews.
    """

    model = ProductReview
    extra = 0
    min_num = 0
    fields: ClassVar[list] = ["user", "rating", "title", "is_active"]
    readonly_fields: ClassVar[list] = ["user", "created_at"]


class PriceHistoryInline(admin.TabularInline):
    """
    Inline admin for viewing price history.
    """

    model = PriceHistory
    extra = 0
    readonly_fields = ["old_price", "new_price", "changed_by", "timestamp"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Product model with comprehensive functionality.
    """

    list_display: ClassVar[list] = [
        "name",
        "sku",
        "category",
        "price_display",  # Shows price + discount
        "cost_price",  # Raw cost price
        "profit_margin_display",  # Profit percentage
        "discount_display",  # Discount percentage
        "stock_display",  # Stock with colors
        "is_in_stock",  # Boolean stock status
        "is_active",
        "status_display",  # Combined status
        "is_featured",
        "average_rating",
        "review_count",
        "created_at",
    ]

    list_filter: ClassVar[list] = [
        "is_active",
        "is_featured",
        "is_digital",
        "requires_shipping",
        "track_inventory",
        "allow_backorders",
        "category",
        "created_at",
        "updated_at",
    ]

    search_fields: ClassVar[list] = [
        "name",
        "sku",
        "description",
        "short_description",
        "category__name",
    ]

    prepopulated_fields: ClassVar[list] = {"slug": ("name",)}

    ordering: ClassVar[list] = ["-created_at"]

    readonly_fields: ClassVar[list] = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "discount_percentage",
        "profit_margin",
        "is_in_stock",
        "is_low_stock",
        "average_rating",
        "review_count",
    ]

    inlines: ClassVar[list] = [
        ProductImageInline,
        ProductSpecificationInline,
        ProductReviewInline,
        PriceHistoryInline,
    ]

    fieldsets: ClassVar[list] = [
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "slug",
                    "sku",
                    "description",
                    "short_description",
                    "category",
                ),
            },
        ),
        (
            "Pricing",
            {
                "fields": (
                    "price",
                    "compare_at_price",
                    "cost_price",
                    "discount_percentage",
                    "profit_margin",
                ),
            },
        ),
        (
            "Inventory",
            {
                "fields": (
                    "stock_quantity",
                    "low_stock_threshold",
                    "track_inventory",
                    "allow_backorders",
                    "is_in_stock",
                    "is_low_stock",
                ),
            },
        ),
        (
            "Physical Properties",
            {
                "fields": (
                    "weight",
                    "dimensions_length",
                    "dimensions_width",
                    "dimensions_height",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Media",
            {
                "fields": ("featured_image",),
            },
        ),
        (
            "Settings",
            {
                "fields": (
                    "is_featured",
                    "is_digital",
                    "requires_shipping",
                    "is_active",
                ),
            },
        ),
        (
            "Availability",
            {
                "fields": ("available_from", "available_until"),
                "classes": ("collapse",),
            },
        ),
        (
            "SEO Settings",
            {
                "fields": ("meta_title", "meta_description", "meta_keywords"),
                "classes": ("collapse",),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    ]

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        queryset = super().get_queryset(request)
        return queryset.select_related("category", "created_by", "updated_by")

    def price_display(self, obj):
        """Display price with discount information."""
        price_html = f"${obj.price.amount}"

        if obj.compare_at_price and obj.compare_at_price.amount > obj.price.amount:
            discount = obj.discount_percentage
            price_html += f" <small style='color: red;'>({discount}% off from ${obj.compare_at_price.amount})</small>"

        return format_html(price_html)

    price_display.short_description = "Price"

    def profit_margin_display(self, obj):
        margin = obj.profit_margin
        if margin is not None:
            return f"{margin:.2f}%"
        return "N/A"

    profit_margin_display.short_description = "Profit Margin"

    def discount_display(self, obj):
        discount = obj.discount_percentage
        if discount:
            return f"{discount:.2f}%"
        return "N/A"

    discount_display.short_description = "Discount"

    def stock_display(self, obj):
        """Display stock information with status indicators."""
        if not obj.track_inventory:
            return format_html("<span style='color: blue;'>Not tracked</span>")

        stock = obj.stock_quantity
        threshold = obj.low_stock_threshold

        if stock <= 0:
            if obj.allow_backorders:
                return format_html(
                    "<span style='color: orange;'>{} (backorders allowed)</span>",
                    stock,
                )
            return format_html(
                "<span style='color: red;'>{} (out of stock)</span>",
                stock,
            )
        if stock <= threshold:
            return format_html(
                "<span style='color: orange;'>{} (low stock)</span>",
                stock,
            )
        return format_html("<span style='color: green;'>{}</span>", stock)

    stock_display.short_description = "Stock"

    def status_display(self, obj):
        """Display product status with indicators."""
        status_parts = []

        if not obj.is_active:
            status_parts.append("<span style='color: red;'>Inactive</span>")
        else:
            status_parts.append("<span style='color: green;'>Active</span>")

        if obj.is_featured:
            status_parts.append("<span style='color: blue;'>Featured</span>")

        if obj.is_digital:
            status_parts.append("<span style='color: purple;'>Digital</span>")

        return format_html(" | ".join(status_parts))

    status_display.short_description = "Status"

    def save_model(self, request, obj, form, change):
        """Set audit fields on save."""
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    actions: ClassVar[list] = [
        "make_featured",
        "remove_featured",
        "activate_products",
        "deactivate_products",
    ]

    def make_featured(self, request, queryset):
        """Mark selected products as featured."""
        count = queryset.update(is_featured=True)
        self.message_user(request, f"{count} products marked as featured.")

    make_featured.short_description = "Mark selected products as featured"

    def remove_featured(self, request, queryset):
        """Remove featured status from selected products."""
        count = queryset.update(is_featured=False)
        self.message_user(request, f"{count} products removed from featured.")

    remove_featured.short_description = "Remove featured status"

    def activate_products(self, request, queryset):
        """Activate selected products."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} products activated.")

    activate_products.short_description = "Activate selected products"

    def deactivate_products(self, request, queryset):
        """Deactivate selected products."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} products deactivated.")

    deactivate_products.short_description = "Deactivate selected products"


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    Admin interface for product images.
    """

    list_display: ClassVar[list] = [
        "product",
        "image_preview",
        "alt_text",
        "is_primary",
        "sort_order",
        "is_active",
        "created_at",
    ]

    list_filter: ClassVar[list] = [
        "is_active",
        "is_primary",
        "product__category",
        "created_at",
    ]

    search_fields: ClassVar[list] = [
        "product__name",
        "product__sku",
        "alt_text",
    ]

    ordering: ClassVar[list] = ["product", "sort_order"]

    readonly_fields: ClassVar[list] = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "image_preview",
    ]

    fieldsets: ClassVar[list] = [
        (
            "Image Information",
            {
                "fields": ("product", "image", "image_preview", "alt_text"),
            },
        ),
        (
            "Display Settings",
            {
                "fields": ("sort_order", "is_primary", "is_active"),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    ]

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("product")

    def image_preview(self, obj):
        """Display image preview in admin."""
        if obj.image:
            return format_html(
                '<img src="{}" alt="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url,
                obj.alt_text or "Product image",
            )
        return "No image"

    image_preview.short_description = "Preview"

    def save_model(self, request, obj, form, change):
        """Set audit fields on save."""
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    """
    Admin interface for product specifications.
    """

    VALUE_PREVIEW_MAX_LENGTH = 50

    list_display: ClassVar[list] = [
        "product",
        "name",
        "value_preview",
        "sort_order",
        "is_active",
        "created_at",
    ]

    list_filter: ClassVar[list] = [
        "is_active",
        "name",
        "product__category",
        "created_at",
    ]

    search_fields: ClassVar[list] = [
        "product__name",
        "product__sku",
        "name",
        "value",
    ]

    ordering: ClassVar[list] = ["product", "sort_order", "name"]

    readonly_fields: ClassVar[list] = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]

    fieldsets: ClassVar[list] = [
        (
            "Specification Information",
            {
                "fields": ("product", "name", "value", "sort_order"),
            },
        ),
        (
            "Settings",
            {
                "fields": ("is_active",),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    ]

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("product")

    def value_preview(self, obj):
        """Display truncated value for long specifications."""
        if len(obj.value) > self.VALUE_PREVIEW_MAX_LENGTH:
            return f"{obj.value[: self.VALUE_PREVIEW_MAX_LENGTH]}..."
        return obj.value

    value_preview.short_description = "Value"

    def save_model(self, request, obj, form, change):
        """Set audit fields on save."""
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """
    Admin interface for product reviews.
    """

    list_display: ClassVar[list] = [
        "product",
        "user",
        "rating",
        "title",
        "is_active",
        "created_at",
    ]
    list_filter: ClassVar[list] = ["is_active", "rating", "created_at"]
    search_fields: ClassVar[list] = ["product__name", "user__email", "title", "comment"]
    readonly_fields: ClassVar[list] = [
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]
    list_select_related: ClassVar[list] = ["product", "user"]
    actions: ClassVar[list] = ["approve_reviews", "disapprove_reviews"]

    def approve_reviews(self, request, queryset):
        queryset.update(is_active=True)

    approve_reviews.short_description = "Approve selected reviews"

    def disapprove_reviews(self, request, queryset):
        queryset.update(is_active=False)

    disapprove_reviews.short_description = "Disapprove selected reviews"


# Custom admin site configuration
admin.site.site_header = "E-commerce Admin"
admin.site.site_title = "E-commerce Admin Portal"
admin.site.index_title = "Welcome to E-commerce Administration"
