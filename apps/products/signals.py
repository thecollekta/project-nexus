# apps/products/signals.py

"""
Signal handlers for products app.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg
from apps.products.models import Product, ProductReview, PriceHistory


@receiver(post_save, sender=ProductReview)
def update_product_rating(sender, instance, created, **kwargs):
    """Update product rating when a review is created or updated."""
    product = instance.product
    
    # Calculate average rating
    avg_rating = ProductReview.objects.filter(
        product=product, 
        is_active=True
    ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    
    # Count total reviews
    review_count = ProductReview.objects.filter(
        product=product, 
        is_active=True
    ).count()
    
    # Update product
    Product.objects.filter(id=product.id).update(
        average_rating=avg_rating,
        review_count=review_count
    )


@receiver(post_delete, sender=ProductReview)
def update_product_rating_on_delete(sender, instance, **kwargs):
    """Update product rating when a review is deleted."""
    product = instance.product
    
    # Calculate average rating
    avg_rating = ProductReview.objects.filter(
        product=product, 
        is_active=True
    ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    
    # Count total reviews
    review_count = ProductReview.objects.filter(
        product=product, 
        is_active=True
    ).count()
    
    # Update product
    Product.objects.filter(id=product.id).update(
        average_rating=avg_rating,
        review_count=review_count
    )


@receiver(post_save, sender=Product)
def track_price_changes(sender, instance, created, **kwargs):
    """Track price changes in PriceHistory."""
    if created:
        return
    
    # Get the previous instance from database
    try:
        old_instance = Product.objects.get(pk=instance.pk)
        if old_instance.price != instance.price:
            PriceHistory.objects.create(
                product=instance,
                old_price=old_instance.price,
                new_price=instance.price,
                changed_by=getattr(instance, 'updated_by', None)
            )
    except Product.DoesNotExist:
        pass
