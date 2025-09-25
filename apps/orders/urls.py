# apps/orders/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.orders.views import CartViewSet, OrderViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"orders", OrderViewSet, basename="orders")

app_name = "orders"

urlpatterns = [
    path("", include(router.urls)),
]
