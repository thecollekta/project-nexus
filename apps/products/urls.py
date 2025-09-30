# apps/products/urls.py

"""
URL configuration for the products app.

Provides comprehensive API endpoints for products, categories, and related models
with both authenticated and public access patterns.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from apps.products.views import (
    CategoryViewSet,
    ProductImageViewSet,
    ProductReviewViewSet,
    ProductSpecificationViewSet,
    ProductViewSet,
    PublicCategoryViewSet,
    PublicProductViewSet,
)

# Main router for authenticated API endpoints
router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"product-images", ProductImageViewSet, basename="product-image")
router.register(
    r"product-specifications",
    ProductSpecificationViewSet,
    basename="product-specification",
)

# Public router for read-only endpoints
public_router = DefaultRouter()
public_router.register(r"products", PublicProductViewSet, basename="public-product")
public_router.register(r"categories", PublicCategoryViewSet, basename="public-category")

# Nested router for reviews under products
products_router = routers.NestedSimpleRouter(router, r"products", lookup="product")
products_router.register(r"reviews", ProductReviewViewSet, basename="product-reviews")

# Add app_name for namespace
app_name = "products"

urlpatterns = [
    # Public API endpoints
    path("public/", include(public_router.urls)),
    # Authenticated API endpoints
    path("", include(router.urls)),
    path("", include(products_router.urls)),
    # Additional public endpoints
    path(
        "public/products/featured/",
        PublicProductViewSet.as_view({"get": "featured"}),
        name="public-product-featured",
    ),
    path(
        "public/products/search/",
        PublicProductViewSet.as_view({"get": "search"}),
        name="public-product-search",
    ),
    path(
        "public/categories/roots/",
        PublicCategoryViewSet.as_view({"get": "roots"}),
        name="public-category-roots",
    ),
    path(
        "public/categories/<uuid:pk>/children/",
        PublicCategoryViewSet.as_view({"get": "children"}),
        name="public-category-children",
    ),
]
