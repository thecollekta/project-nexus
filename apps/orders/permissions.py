# apps/orders/permissions.py

from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission that allows access to owners or admin users.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user owns the object or is admin."""
        # Admin users have full access
        if request.user.is_staff:
            return True

        # Check if user owns the object
        if hasattr(obj, "user"):
            return obj.user == request.user

        # For cart objects without user (guest carts)
        if hasattr(obj, "session_key") and not obj.user:
            session_key = request.session.session_key
            return obj.session_key == session_key

        return False


class IsOrderOwnerOrAdmin(permissions.BasePermission):
    """
    Permission that allows access to order owners or admin users.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user owns the order or is admin."""
        # Admin users have full access
        if request.user.is_staff:
            return True

        # Users can access their own orders
        return obj.user == request.user


class IsAdminUser(permissions.BasePermission):
    """
    Permission that only allows access to admin users.
    """

    def has_permission(self, request, view):
        """Check if user is admin."""
        return request.user and request.user.is_authenticated and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        """Admin users have access to all objects."""
        return request.user.is_staff


class CanManageOrder(permissions.BasePermission):
    """
    Permission for order management operations like shipping, cancellation.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check permissions based on action."""
        action = getattr(view, "action", None)

        # Admin users can perform all actions
        if request.user.is_staff:
            return True

        # Users can cancel their own orders (if cancellable)
        if action == "cancel":
            return obj.user == request.user and obj.can_be_cancelled()

        # Only admin can ship orders, mark as delivered, etc.
        if action in ["ship", "delivered", "update"]:
            return False

        # Users can view their own orders
        if action in ["retrieve", "track"]:
            return obj.user == request.user

        return False
