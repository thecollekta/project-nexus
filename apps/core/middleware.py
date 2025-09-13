# apps/core/middleware.py

"""
Django middleware for user tracking in request/response cycle.

This module provides middleware to track the current user making the request
and make this information available throughout the request/response cycle.
It's particularly useful for audit logging and automatic user tracking in models.
"""

import threading
from collections.abc import Callable

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
            response = self.get_response(request)
            return response
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
    def resolve(self, next, root, info, **args):
        # Add performance tracking
        import time

        start_time = time.time()
        result = next(root, info, **args)
        duration = time.time() - start_time

        # Log slow queries
        if duration > 1.0:  # More than 1 second
            print(f"Slow GraphQL query: {info.operation.name} took {duration:.2f}s")

        return result
