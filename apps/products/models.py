# apps/products/models.py

"""
Product catalog models for the e-commerce application.

This module contains the core models for managing products, categories,
and related functionality like inventory tracking, pricing, and SEO optimization.
"""

from decimal import Decimal
from typing import ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import (ActiveManager, AllObjectsManager,
                              AuditStampedModelBase)


class CategoryManager(ActiveManager):
    """Custom manager for Category model."""

    def get_root_categories(self):
        """Get all root categories (categories without parent)."""
        return self.get_queryset().filter(parent__isnull=True)

    def get_featured_categories(self):
        """Get all featured categories."""
        return self.get_queryset().filter(is_featured=True)


class Category(AuditStampedModelBase):
    """
    Product category model with hierarchical structure support.

    Categories can be nested to create a tree-like structure for better
    product organization and navigation.
    """

    name = models.CharField(
        max_length=255,
        help_text=_("Category name"),
        db_index=True,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text=_("URL-friendly category identifier"),
        db_index=True,
    )

    description = models.TextField(
        blank=True,
        help_text=_("Category description"),
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text=_("Parent category for hierarchical structure"),
        db_index=True,
    )

    image = models.ImageField(
        upload_to="categories/images/",
        blank=True,
        null=True,
        help_text=_("Category image"),
    )

    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("CSS class or icon identifier for category"),
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Sort order for display"),
        db_index=True,
    )

    is_featured = models.BooleanField(
        default=False,
        help_text=_("Whether this category is featured"),
        db_index=True,
    )

    # SEO fields
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("SEO meta title"),
    )

    meta_description = models.TextField(
        max_length=500,
        blank=True,
        help_text=_("SEO meta description"),
    )

    meta_keywords = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("SEO meta keywords (comma-separated)"),
    )

    # Custom managers
    objects = CategoryManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering: ClassVar[list] = ["sort_order", "name"]
        indexes: ClassVar[list] = [
            models.Index(fields=["parent", "is_active"]),
            models.Index(fields=["is_featured", "is_active"]),
            models.Index(fields=["sort_order", "name"]),
        ]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["name", "parent"],
                name="unique_category_name_per_parent",
            ),
        ]

    def __str__(self) -> str:
        """Return category name with parent hierarchy."""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        """Override save to auto-generate slug and validate hierarchy."""
        if not self.slug:
            self.slug = slugify(self.name)

        # Ensure slug is unique
        if Category.all_objects.exclude(id=self.id).filter(slug=self.slug).exists():
            counter = 1
            original_slug = self.slug
            while (
                Category.all_objects.exclude(id=self.id).filter(slug=self.slug).exists()
            ):
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    def clean(self):
        """Validate that category doesn't become its own parent."""
        if self.parent and self.parent.id == self.id:
            raise ValidationError(_("A category cannot be its own parent."))

        # Check for circular references
        parent = self.parent
        while parent:
            if parent.id == self.id:
                raise ValidationError(
                    _("Circular reference detected in category hierarchy."),
                )
            parent = parent.parent

        # Add uniqueness validation
        if (
            Category.all_objects.filter(
                name=self.name,
                parent=self.parent,
            )
            .exclude(id=self.id)
            .exists()
        ):
            if self.parent:
                raise ValidationError(
                    _(
                        "A category with this name already exists under the same parent.",
                    ),
                )
            raise ValidationError(
                _("A root category with this name already exists."),
            )

    def get_ancestors(self):
        """Get all ancestor categories."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors[::-1]  # Reverse to get root first

    def get_descendants(self):
        """Get all descendant categories."""
        descendants = []

        def collect_descendants(category):
            for child in category.children.filter(is_active=True):
                descendants.append(child)
                collect_descendants(child)

        collect_descendants(self)
        return descendants

    def get_level(self):
        """Get the level of this category in the hierarchy (0 for root)."""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level

    @property
    def product_count(self) -> int:
        """Get the number of active products in this category.

        Returns:
            int: The count of active products in this category
        """
        return self.products.filter(is_active=True).count()  # type: ignore

    @property
    def total_product_count(self) -> int:
        """Get the total number of products including subcategories.

        Returns:
            int: The total count of products in this category and all its subcategories
        """
        count = self.product_count
        for child in self.children.filter(is_active=True):  # type: ignore
            count += child.total_product_count
        return count


class ProductManager(ActiveManager):
    """Custom manager for Product model."""

    def get_featured_products(self):
        """Get all featured products."""
        return self.get_queryset().filter(is_featured=True)

    def get_in_stock_products(self):
        """Get all products that are in stock."""
        return self.get_queryset().filter(stock_quantity__gt=0)

    def get_by_category(self, category):
        """Get all products in a specific category."""
        return self.get_queryset().filter(category=category)

    def get_by_price_range(self, min_price=None, max_price=None):
        """Get products within a price range."""
        queryset = self.get_queryset()
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        return queryset


class Product(AuditStampedModelBase):
    """
    Product model representing items in the catalog.

    Contains comprehensive product information including pricing,
    inventory, SEO data, and relationships to categories.
    """

    # Basic product information
    name = models.CharField(
        max_length=255,
        help_text=_("Product name"),
        db_index=True,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text=_("URL-friendly product identifier"),
        db_index=True,
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Stock Keeping Unit - unique product identifier"),
        db_index=True,
    )

    description = models.TextField(
        help_text=_("Detailed product description"),
    )

    short_description = models.TextField(
        max_length=500,
        blank=True,
        help_text=_("Brief product description for listings"),
    )

    # Categorization
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        help_text=_("Primary product category"),
        db_index=True,
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Product price"),
        db_index=True,
    )

    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Original price for comparison (shows discount)"),
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Cost price for margin calculation"),
    )

    # Inventory
    stock_quantity = models.PositiveIntegerField(
        default=0,
        help_text=_("Current stock quantity"),
        db_index=True,
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text=_("Quantity threshold for low stock alerts"),
    )

    track_inventory = models.BooleanField(
        default=True,
        help_text=_("Whether to track inventory for this product"),
    )

    allow_backorders = models.BooleanField(
        default=False,
        help_text=_("Allow orders when out of stock"),
    )

    # Physical properties
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Product weight in kg"),
    )

    dimensions_length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Product length in cm"),
    )

    dimensions_width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Product width in cm"),
    )

    dimensions_height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Product height in cm"),
    )

    # Media
    featured_image = models.ImageField(
        upload_to="products/images/",
        null=True,
        blank=True,
        help_text=_("Primary product image"),
    )

    # Status flags
    is_featured = models.BooleanField(
        default=False,
        help_text=_("Whether this product is featured"),
        db_index=True,
    )

    is_digital = models.BooleanField(
        default=False,
        help_text=_("Whether this is a digital product"),
    )

    requires_shipping = models.BooleanField(
        default=True,
        help_text=_("Whether this product requires shipping"),
    )

    # SEO fields
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("SEO meta title"),
    )

    meta_description = models.TextField(
        max_length=500,
        blank=True,
        help_text=_("SEO meta description"),
    )

    meta_keywords = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("SEO meta keywords (comma-separated)"),
    )

    # Timestamps for availability
    available_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Product availability start date"),
    )

    available_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Product availability end date"),
    )

    # Custom managers
    objects = ProductManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering: ClassVar[list] = ["-created_at"]
        indexes: ClassVar[list] = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["is_featured", "is_active"]),
            models.Index(fields=["price", "is_active"]),
            models.Index(fields=["stock_quantity", "track_inventory"]),
            models.Index(fields=["sku", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """Override save to auto-generate slug and handle SEO fields."""
        if not self.slug:
            self.slug = slugify(self.name)

        # Ensure slug is unique
        if Product.all_objects.exclude(id=self.id).filter(slug=self.slug).exists():
            counter = 1
            original_slug = self.slug
            while (
                Product.all_objects.exclude(id=self.id).filter(slug=self.slug).exists()
            ):
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        # Auto-generate meta title if not provided
        if not self.meta_title:
            self.meta_title = self.name

        # Auto-generate meta description if not provided
        if not self.meta_description and self.short_description:
            self.meta_description = self.short_description

        super().save(*args, **kwargs)

    def clean(self):
        """Validate product data."""
        if self.compare_at_price and self.compare_at_price <= self.price:
            raise ValidationError(
                _("Compare at price must be higher than the regular price."),
            )

        if (
            self.available_from
            and self.available_until
            and self.available_from >= self.available_until
        ):
            raise ValidationError(
                _("Available from date must be before available until date."),
            )

    @property
    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0 or self.allow_backorders

    @property
    def is_low_stock(self) -> bool:
        """Check if product has low stock."""
        if not self.track_inventory:
            return False
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def discount_percentage(self) -> Decimal | None:
        """Calculate discount percentage if compare_at_price is set."""
        if not self.compare_at_price or self.compare_at_price <= self.price:
            return None
        discount = self.compare_at_price - self.price
        return round((discount / self.compare_at_price) * 100, 2)

    @property
    def profit_margin(self) -> Decimal | None:
        """Calculate profit margin if cost_price is set."""
        if not self.cost_price:
            return None
        profit = self.price - self.cost_price
        return round((profit / self.price) * 100, 2)

    def reduce_stock(self, quantity: int) -> bool:
        """
        Reduce stock quantity by the specified amount.
        Returns True if successful, False if insufficient stock.
        """
        if not self.track_inventory:
            return True

        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save(update_fields=["stock_quantity", "updated_at"])
            return True

        return self.allow_backorders

    def increase_stock(self, quantity: int) -> None:
        """Increase stock quantity by the specified amount."""
        if self.track_inventory:
            self.stock_quantity += quantity
            self.save(update_fields=["stock_quantity", "updated_at"])


class ProductImage(AuditStampedModelBase):
    """
    Additional product images model.
    Allows multiple images per product for galleries.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        help_text=_("Product this image belongs to"),
    )

    image = models.ImageField(
        upload_to="products/gallery/",
        help_text=_("Product image"),
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Alternative text for accessibility"),
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Sort order for image display"),
    )

    is_primary = models.BooleanField(
        default=False,  # Default to False to ensure explicit primary image selection
        help_text=_("Whether this is the primary image"),
    )

    # Custom managers
    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")
        ordering: ClassVar[list] = ["sort_order", "created_at"]
        indexes: ClassVar[list] = [
            models.Index(fields=["product", "is_primary"]),
            models.Index(fields=["product", "sort_order"]),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} - Image {self.id}"

    def save(self, *args, **kwargs):
        """Override save to handle primary image logic."""
        # If this is marked as primary, unmark other primary images for this product
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True,
            ).exclude(
                id=self.id
            ).update(is_primary=False)

        # Auto-generate alt text if not provided
        if not self.alt_text:
            self.alt_text = f"{self.product.name} image"

        super().save(*args, **kwargs)


class ProductSpecification(AuditStampedModelBase):
    """
    Product specifications model for storing key-value pairs.
    Allows flexible product attributes without schema changes.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="specifications",
        help_text=_("Product this specification belongs to"),
    )

    name = models.CharField(
        max_length=255,
        help_text=_("Specification name/key"),
        db_index=True,
    )

    value = models.TextField(
        help_text=_("Specification value"),
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Sort order for specification display"),
    )

    # Custom managers
    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = _("Product Specification")
        verbose_name_plural = _("Product Specifications")
        ordering: ClassVar[list] = ["sort_order", "name"]
        unique_together: ClassVar[list] = ["product", "name"]
        indexes: ClassVar[list] = [
            models.Index(fields=["product", "sort_order"]),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} - {self.name}: {self.value}"
