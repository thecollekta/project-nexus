# apps/products/signals.py

"""
Django signals for the products app.

Handles automatic slug generation, audit tracking, and business logic
for product and category operations.
"""

import structlog
from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from apps.core.middleware import get_current_user
from apps.products.models import Category, Product, ProductImage, ProductReview

# Set up logging
logger = structlog.get_logger(__name__)


@receiver(pre_save, sender=Category)
def category_pre_save(sender, instance, **kwargs):
    """
    Handle category pre-save operations.
    """
    current_user = get_current_user()

    # Auto-generate slug if not provided
    if not instance.slug and instance.name:
        base_slug = slugify(instance.name)
        slug = base_slug
        counter = 1

        # Ensure slug uniqueness
        while Category.all_objects.exclude(id=instance.id).filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        instance.slug = slug

    # Set audit fields
    if current_user and current_user.is_authenticated:
        if not instance.pk:  # New instance
            instance.created_by = current_user
        instance.updated_by = current_user

    # Auto-generate meta title if not provided
    if not instance.meta_title and instance.name:
        instance.meta_title = instance.name


@receiver(post_save, sender=Category)
def category_post_save(sender, instance, created, **kwargs):
    """
    Handle category post-save operations.
    """
    action = "created" if created else "updated"

    logger.info(
        f"category_{action}",
        category_id=instance.id,
        category_name=instance.name,
        category_slug=instance.slug,
        parent_id=instance.parent.id if instance.parent else None,
        is_active=instance.is_active,
        user_id=instance.updated_by.id if instance.updated_by else None,
    )


@receiver(pre_save, sender=Product)
def product_pre_save(sender, instance, **kwargs):
    """
    Handle product pre-save operations.
    """
    current_user = get_current_user()

    # Auto-generate slug if not provided
    if not instance.slug and instance.name:
        base_slug = slugify(instance.name)
        slug = base_slug
        counter = 1

        # Ensure slug uniqueness
        while Product.all_objects.exclude(id=instance.id).filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        instance.slug = slug

    # Normalize SKU to uppercase
    if instance.sku:
        instance.sku = instance.sku.strip().upper()

    # Set audit fields
    if current_user and current_user.is_authenticated:
        if not instance.pk:  # New instance
            instance.created_by = current_user
        instance.updated_by = current_user

    # Auto-generate meta fields if not provided
    if not instance.meta_title and instance.name:
        instance.meta_title = instance.name

    if not instance.meta_description and instance.short_description:
        instance.meta_description = instance.short_description

    # Business logic for digital products
    if instance.is_digital:
        instance.requires_shipping = False
        instance.weight = None
        instance.dimensions_length = None
        instance.dimensions_width = None
        instance.dimensions_height = None


@receiver(post_save, sender=Product)
def product_post_save(sender, instance, created, **kwargs):
    """
    Handle product post-save operations.
    """
    action = "created" if created else "updated"

    # Log the product operation
    logger.info(
        f"product_{action}",
        product_id=instance.id,
        product_name=instance.name,
        product_slug=instance.slug,
        product_sku=instance.sku,
        category_id=instance.category.id,
        price=str(instance.price),
        stock_quantity=instance.stock_quantity,
        is_active=instance.is_active,
        is_featured=instance.is_featured,
        user_id=instance.updated_by.id if instance.updated_by else None,
    )

    # Check for low stock alert
    if (
        instance.track_inventory
        and instance.stock_quantity <= instance.low_stock_threshold
        and instance.stock_quantity > 0
    ):
        logger.warning(
            "product_low_stock_alert",
            product_id=instance.id,
            product_name=instance.name,
            product_sku=instance.sku,
            current_stock=instance.stock_quantity,
            threshold=instance.low_stock_threshold,
        )

    # Check for out of stock alert
    if (
        instance.track_inventory
        and instance.stock_quantity == 0
        and not instance.allow_backorders
    ):
        logger.warning(
            "product_out_of_stock_alert",
            product_id=instance.id,
            product_name=instance.name,
            product_sku=instance.sku,
        )


@receiver(post_save, sender=ProductImage)
def product_image_post_save(sender, instance, created, **kwargs):
    """
    Handle product image post-save operations.
    """
    # Auto-generate alt text if not provided
    if not instance.alt_text:
        instance.alt_text = f"{instance.product.name} image"
        # Update without triggering signals again
        ProductImage.all_objects.filter(id=instance.id).update(
            alt_text=instance.alt_text,
        )

    # Set as primary if this is the first image for the product
    if (
        created
        and not ProductImage.objects.filter(
            product=instance.product,
            is_primary=True,
        ).exists()
    ):
        instance.is_primary = True
        ProductImage.all_objects.filter(id=instance.id).update(is_primary=True)

    # Log image operation
    action = "added" if created else "updated"
    logger.info(
        f"product_image_{action}",
        product_id=instance.product.id,
        image_id=instance.id,
        is_primary=instance.is_primary,
        sort_order=instance.sort_order,
    )


@receiver(post_delete, sender=ProductImage)
def product_image_post_delete(sender, instance, **kwargs):
    """
    Handle product image deletion.
    """
    # If the deleted image was primary, set another image as primary
    if instance.is_primary:
        remaining_images = ProductImage.objects.filter(
            product=instance.product,
        ).order_by("sort_order")
        if remaining_images.exists():
            new_primary = remaining_images.first()
            new_primary.is_primary = True
            new_primary.save()

            logger.info(
                "product_primary_image_reassigned",
                product_id=instance.product.id,
                old_primary_id=instance.id,
                new_primary_id=new_primary.id,
            )

    logger.info(
        "product_image_deleted",
        product_id=instance.product.id,
        image_id=instance.id,
        was_primary=instance.is_primary,
    )


@receiver(post_save, sender=ProductReview)
@receiver(post_delete, sender=ProductReview)
def update_product_rating(sender, instance, **kwargs):
    """
    Recalculate and update the product's average rating and review count
    whenever a review is saved or deleted.
    """
    product = instance.product

    # Use aggregation to calculate the new average rating and count
    active_reviews = ProductReview.objects.filter(product=product, is_active=True)

    aggregation = active_reviews.aggregate(
        new_average=Avg("rating"), new_count=Count("id")
    )

    product.average_rating = aggregation.get("new_average") or 0
    product.review_count = aggregation.get("new_count") or 0

    product.save(update_fields=["average_rating", "review_count", "updated_at"])

    logger.info(
        "product_rating_updated",
        product_id=product.id,
        new_average_rating=float(product.average_rating),
        review_count=product.review_count,
    )
