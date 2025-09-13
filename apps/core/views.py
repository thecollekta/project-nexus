# apps/core/views.py

"""
Base viewsets with logging, throttling, and common functionality.
Provides a foundation for all API views in the e-commerce application.
"""

import structlog
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

# Set up logging
logger = structlog.get_logger(__name__)


class LoggingMixin:
    """
    Mixin that provides comprehensive logging for viewset actions.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = None

    def log_action(self, action_name, extra_data=None):
        """
        Log an action with context information.
        """
        user_info = "Anonymous"
        if (
            hasattr(self, "request")
            and self.request
            and hasattr(self.request, "user")
            and self.request.user
            and self.request.user.is_authenticated
        ):
            user_info = f"User {self.request.user.id} ({self.request.user.username})"

        log_data = {
            "action": action_name,
            "viewset": self.__class__.__name__,
            "user": user_info,
            "timestamp": timezone.now().isoformat(),
            "ip_address": self.get_client_ip(),
        }

        if extra_data:
            log_data.update(extra_data)

        logger.info(f"API Action: {action_name}", extra=log_data)

    def get_client_ip(self):
        """
        Get the client's IP address from the request.
        """
        if not self.request:
            return None
        x_forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = self.request.META.get("REMOTE_ADDR")
        return ip


class BaseViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    Base viewset that provides common functionality for all API views.
    Includes logging, throttling, error handling, and standard responses.
    """

    # Default throttling - can be overridden in child classes
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.
        """
        super().initial(request, *args, **kwargs)

        # Log the incoming request
        self.log_action(
            f"{request.method} {self.action}",
            extra_data={
                "path": request.path,
                "query_params": dict(request.query_params),
            },
        )

    def handle_exception(self, exc):
        """
        Handle any exception that occurs, logging it appropriately.
        """
        self.log_action(
            "error",
            extra_data={
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )

        # Log to system logger as well
        logger.error(
            f"Exception in {self.__class__.__name__}: {exc}",
            exc_info=True,
            extra={
                "viewset": self.__class__.__name__,
                "user_id": getattr(self.request.user, "id", None),
                "path": self.request.path,
            },
        )

        return super().handle_exception(exc)

    def list(self, request, *args, **kwargs):
        """
        Override list to add logging and custom response format.
        """
        try:
            response = super().list(request, *args, **kwargs)

            results = (
                response.data.get("results", [])
                if response and hasattr(response, "data") and response.data
                else []
            )
            self.log_action(
                "list_success",
                extra_data={
                    "count": len(results),
                    "page": request.query_params.get("page", 1),
                },
            )

            return response

        except Exception as e:
            logger.error(f"Error in list view: {e}")
            return Response(
                {"error": "An error occurred while fetching data"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve to add logging.
        """
        try:
            response = super().retrieve(request, *args, **kwargs)

            self.log_action(
                "retrieve_success", extra_data={"object_id": kwargs.get("pk")}
            )

            return response

        except Exception as e:
            logger.error(f"Error in retrieve view: {e}")
            return Response(
                {"error": "Object not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Override create to add logging and transaction handling.
        """
        try:
            response = super().create(request, *args, **kwargs)

            created_id = (
                response.data.get("id")
                if response and hasattr(response, "data") and response.data
                else None
            )
            self.log_action(
                "create_success",
                extra_data={"created_object_id": created_id},
            )

            return response

        except Exception as e:
            logger.error(f"Error in create view: {e}")
            return Response(
                {"error": "An error occurred while creating the object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Override update to add logging and transaction handling.
        """
        try:
            response = super().update(request, *args, **kwargs)

            self.log_action(
                "update_success", extra_data={"updated_object_id": kwargs.get("pk")}
            )

            return response

        except Exception as e:
            logger.error(f"Error in update view: {e}")
            return Response(
                {"error": "An error occurred while updating the object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to implement soft delete and add logging.
        """
        try:
            instance = self.get_object()

            # Perform soft delete instead of hard delete
            if hasattr(instance, "soft_delete"):
                instance.soft_delete()
                self.log_action(
                    "soft_delete_success",
                    extra_data={"deleted_object_id": kwargs.get("pk")},
                )
            else:
                # Fallback to hard delete if soft delete not available
                instance.delete()
                self.log_action(
                    "hard_delete_success",
                    extra_data={"deleted_object_id": kwargs.get("pk")},
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error in destroy view: {e}")
            return Response(
                {"error": "An error occurred while deleting the object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def restore(self, request, pk=None):
        """
        Custom action to restore soft-deleted objects.
        Only available to authenticated users.
        """
        try:
            instance = self.get_object()

            if hasattr(instance, "restore"):
                instance.restore()
                self.log_action(
                    "restore_success", extra_data={"restored_object_id": pk}
                )
                return Response({"message": "Object restored successfully"})
            else:
                return Response(
                    {"error": "Restore operation not supported"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error in restore action: {e}")
            return Response(
                {"error": "An error occurred while restoring the object"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BaseReadOnlyViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    """
    Base viewset for read-only operations.
    Useful for reference data or public information that shouldn't be modified via API.
    """

    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def list(self, request, *args, **kwargs):
        """Override list to add logging."""
        response = super().list(request, *args, **kwargs)

        results = (
            response.data.get("results", [])
            if response and hasattr(response, "data") and response.data
            else []
        )
        self.log_action(
            "readonly_list_success",
            extra_data={"count": len(results)},
        )

        return response

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to add logging."""
        response = super().retrieve(request, *args, **kwargs)

        self.log_action(
            "readonly_retrieve_success", extra_data={"object_id": kwargs.get("pk")}
        )

        return response


# Example usage:
"""
from core.views import BaseViewSet
from apps.models import Product
from apps.serializers import ProductSerializer

class ProductViewSet(BaseViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        # Custom queryset logic
        queryset = super().get_queryset()

        # Add any filtering logic here
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)

        return queryset
"""
