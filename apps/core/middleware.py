# apps/core/middleware.py

"""
Django middleware for user tracking in request/response cycle.

This module provides middleware to track the current user making the request
and make this information available throughout the request/response cycle.
It's particularly useful for audit logging and automatic user tracking in models.
"""

import threading
import time
from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse

# Thread local storage for the current request
_request = threading.local()


class CurrentUserMiddleware:
    """Middleware to make the current user and request available in models."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Set the current request and user in thread local storage
        _request.user = getattr(request, "user", None)
        _request.request = request

        try:
            return self.get_response(request)
        finally:
            # Clean up after the response is processed
            if hasattr(_request, "user"):
                del _request.user
            if hasattr(_request, "request"):
                del _request.request


def get_current_user():
    """
    Get the current user from thread local storage.
    Returns None if no user is logged in or if called outside of a request.
    """
    return getattr(_request, "user", None)


def get_current_request():
    """
    Get the current request from thread local storage.
    Returns None if called outside of a request.
    """
    return getattr(_request, "request", None)


class PerformanceMiddleware:
    def resolve(self, next_resolver, root, info, **args):
        # Add performance tracking
        start_time = time.time()
        result = next_resolver(root, info, **args)
        duration = time.time() - start_time

        try:
            logger = structlog.get_logger("graphql.performance")
            operation = getattr(getattr(info, "operation", None), "name", None)
            op_name = getattr(operation, "value", None) if operation else None
            field = getattr(info, "field_name", None)
            parent_type = getattr(getattr(info, "parent_type", None), "name", None)

            if duration > 1.0:
                logger.warning(
                    "graphql_field_slow",
                    operation=op_name,
                    parent_type=parent_type,
                    field=field,
                    duration_ms=int(duration * 1000),
                )
            else:
                logger.info(
                    "graphql_field",
                    operation=op_name,
                    parent_type=parent_type,
                    field=field,
                    duration_ms=int(duration * 1000),
                )
        except Exception as e:
            logger = structlog.get_logger("graphql.performance")
            logger.exception("graphql_performance_logging_failed", error=str(e))

        return result
