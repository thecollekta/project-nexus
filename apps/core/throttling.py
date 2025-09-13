# apps/core/throttling.py

"""
Custom throttling classes for rate limiting API requests.
Provides different throttling rates for different user types and actions.
"""

from django.core.cache import cache
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class CustomAnonRateThrottle(AnonRateThrottle):
    """
    Custom throttling for anonymous users.
    More restrictive to prevent abuse.
    """

    scope = "anon"

    def allow_request(self, request, view):
        """
        Override to add custom logic for anonymous users.
        """
        # Log throttling attempts for monitoring
        result = super().allow_request(request, view)

        if not result:
            # Log when anonymous users hit rate limits
            cache_key = f"throttle_blocked_anon_{self.get_ident(request)}"
            cache.set(cache_key, True, timeout=60)  # Track for 1 minute

        return result


class CustomUserRateThrottle(UserRateThrottle):
    """
    Custom throttling for authenticated users.
    More permissive than anonymous users.
    """

    scope = "user"

    def allow_request(self, request, view):
        """
        Override to add custom logic for authenticated users.
        """
        result = super().allow_request(request, view)

        if not result and request.user.is_authenticated:
            # Log when authenticated users hit rate limits
            cache_key = f"throttle_blocked_user_{request.user.pk}"
            cache.set(cache_key, True, timeout=60)

        return result


class AdminRateThrottle(UserRateThrottle):
    """
    More permissive throttling for admin users.
    Allows higher request rates for administrative tasks.
    """

    scope = "admin"

    def allow_request(self, request, view):
        """
        Check if user is admin and apply appropriate rate limiting.
        """
        if request.user and request.user.is_authenticated and request.user.is_staff:  # type: ignore
            return super().allow_request(request, view)

        # If not admin, fall back to regular user throttling
        regular_throttle = CustomUserRateThrottle()
        return regular_throttle.allow_request(request, view)


class BurstRateThrottle(UserRateThrottle):
    """
    Handles burst requests - allows higher rate for short periods.
    Useful for APIs that might need quick successive calls.
    """

    scope = "burst"


class LoginRateThrottle(AnonRateThrottle):
    """
    Special throttling for login attempts to prevent brute force attacks.
    Very restrictive to enhance security.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        """
        Use IP address for login throttling regardless of authentication status.
        """
        if request.user and request.user.is_authenticated:
            # Even if somehow authenticated, still throttle by IP for login endpoints
            ident = self.get_ident(request)
        else:
            ident = self.get_ident(request)

        return self.cache_format % {"scope": self.scope, "ident": ident}


class CreateAccountRateThrottle(AnonRateThrottle):
    """
    Throttling for account creation to prevent spam registrations.
    """

    scope = "register"

    def get_cache_key(self, request, view):
        """
        Use IP address for registration throttling.
        """
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Throttling for password reset requests to prevent abuse.
    """

    scope = "password_reset"


class APIKeyRateThrottle(UserRateThrottle):
    """
    Special throttling for API key based authentication.
    Can be used for third-party integrations.
    """

    scope = "api_key"

    def get_cache_key(self, request, view) -> str:
        """
        Use API key for throttling instead of user ID.
        Falls back to IP-based identification if no API key is present.
        """
        api_key = request.META.get("HTTP_X_API_KEY")
        if not api_key:
            ident = self.get_ident(request)
        else:
            ident = api_key

        return self.cache_format % {"scope": self.scope, "ident": ident}


# Throttling utilities
class ThrottlingUtils:
    """
    Utility functions for working with throttling.
    """

    @staticmethod
    def get_throttle_classes_for_user(user, action=None):
        """
        Returns appropriate throttle classes based on user type and action.
        """
        if not user or not user.is_authenticated:
            # Anonymous users
            throttles = [CustomAnonRateThrottle]

            # Special cases for anonymous users
            if action in ["login", "create_account", "password_reset"]:
                throttles.append(
                    {
                        "login": LoginRateThrottle,
                        "create_account": CreateAccountRateThrottle,
                        "password_reset": PasswordResetRateThrottle,
                    }[action]
                )

            return throttles

        elif user.is_staff:
            # Admin users get more permissive throttling
            return [AdminRateThrottle, BurstRateThrottle]

        else:
            # Regular authenticated users
            return [CustomUserRateThrottle, BurstRateThrottle]

    @staticmethod
    def is_user_throttled(request):
        """
        Check if a user is currently being throttled.
        """
        if request.user.is_authenticated:
            cache_key = f"throttle_blocked_user_{request.user.id}"
        else:
            # For anonymous users, use IP
            cache_key = f"throttle_blocked_anon_{request.META.get('REMOTE_ADDR')}"

        return cache.get(cache_key, False)

    @staticmethod
    def get_throttle_status(request, throttle_class):
        """
        Get detailed throttling status for monitoring.
        """
        throttle = throttle_class()

        # Get the current count and limits
        key = throttle.get_cache_key(request, None)
        if not key:
            return None

        history = throttle.cache.get(key, [])
        now = throttle.timer()

        # Count requests within the time window
        while history and history[-1] <= now - throttle.duration:
            history.pop()

        return {
            "requests_made": len(history),
            "requests_allowed": throttle.num_requests,
            "time_window": throttle.duration,
            "requests_remaining": max(0, throttle.num_requests - len(history)),
            "reset_time": now + throttle.duration if history else now,
        }


# Example usage in views:
"""
from rest_framework.decorators import action
from apps.core.throttling import LoginRateThrottle, CreateAccountRateThrottle

class UserViewSet(BaseViewSet):

    @action(detail=False, methods=['post'], throttle_classes=[LoginRateThrottle])
    def login(self, request):
        # Login logic here
        pass

    @action(detail=False, methods=['post'], throttle_classes=[CreateAccountRateThrottle])
    def register(self, request):
        # Registration logic here
        pass

    def get_throttles(self):
        \"\"\"
        Override to apply different throttling based on action.
        \"\"\"
        from apps.core.throttling import ThrottlingUtils

        throttle_classes = ThrottlingUtils.get_throttle_classes_for_user(
            self.request.user,
            self.action
        )

        return [throttle() for throttle in throttle_classes]
"""
