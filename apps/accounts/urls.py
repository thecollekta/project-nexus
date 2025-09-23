# apps/accounts/urls.py

"""
URL configuration for the accounts app.
Defines API endpoints for user authentication and profile management.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    CustomTokenRefreshView,
    UserLoginView,
    UserLogoutView,
    UserProfileViewSet,
    UserRegistrationView,
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r"profiles", UserProfileViewSet, basename="user-profile")
router.register(
    r"users",
    UserProfileViewSet,
    basename="user",
)  # For admin user management

# Add app_name for namespace
app_name = "accounts"

# Define URL patterns
urlpatterns = [
    # Authentication endpoints
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    path("login/", UserLoginView.as_view(), name="user-login"),
    path("logout/", UserLogoutView.as_view(), name="user-logout"),
    # Profile management
    path(
        "me/",
        UserProfileViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
            },
        ),
        name="user-profile-me",
    ),
    path(
        "me/change-password/",
        UserProfileViewSet.as_view({"post": "change_password"}),
        name="user-password-change",
    ),
    # Email verification
    path(
        "verify-email/",
        UserProfileViewSet.as_view({"post": "request_verification_email"}),
        name="user-verify-email",
    ),
    path(
        "verify-email/confirm/",
        UserProfileViewSet.as_view({"post": "verify_email"}),
        name="user-verify-email-confirm",
    ),
    # JWT token management
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token-refresh"),
    # Password reset confirm
    path(
        "reset-password/confirm/",
        UserProfileViewSet.as_view({"post": "reset_password_confirm"}),
        name="user-password-reset-confirm",
    ),
    # Include router URLs last
    path("", include(router.urls)),
]
