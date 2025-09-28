# ecommerce_backend/middleware.py

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin


class AuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(request, "user"):
            request.user = AnonymousUser()
        return None


class SensitiveDataMiddleware(MiddlewareMixin):
    """
    Middleware to remove sensitive information from responses.
    Reduces payload size and prevents accidental exposure of sensitive data.
    """

    SENSITIVE_HEADERS = {
        "X-Powered-By",
        "X-AspNet-Version",
        "X-AspNetMvc-Version",
        "Server",
        "X-Debug-Token",
        "X-Debug-Token-Link",
    }

    SENSITIVE_COOKIES = {
        "sessionid",
        "csrftoken",
        "_ga",
        "_gid",
        "_gat",
    }

    def process_response(self, request, response):
        # Remove sensitive headers
        for header in self.SENSITIVE_HEADERS:
            if header in response:
                del response[header]

        # Remove detailed error information in production
        if not settings.DEBUG and hasattr(response, "data"):
            if isinstance(response.data, dict) and "detail" in response.data:
                # Keep only the error message, remove stack traces and other details
                if "error_code" in response.data:
                    del response.data["error_code"]
                if "traceback" in response.data:
                    del response.data["traceback"]

        return response


class PayloadOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware to optimize response payload size.
    """

    def process_response(self, request, response):
        # Only process JSON responses
        if hasattr(response, "data") and isinstance(response.data, dict):
            self._optimize_payload(response.data)

        return response

    def _optimize_payload(self, data):
        """Recursively optimize payload by removing null/empty values."""
        if isinstance(data, dict):
            # Remove null values and empty strings
            keys_to_remove = [
                key
                for key, value in data.items()
                if value is None
                or value == ""
                or (isinstance(value, (dict, list)) and not value)
            ]
            for key in keys_to_remove:
                del data[key]

            # Recursively process remaining values
            for value in data.values():
                self._optimize_payload(value)

        elif isinstance(data, list):
            for item in data:
                self._optimize_payload(item)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers and prevent information disclosure.
    """

    def process_response(self, request, response):
        # Security headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Remove server version information
        if "Server" in response:
            del response["Server"]

        return response


class DebugToolbarConditionalMiddleware(MiddlewareMixin):
    """
    Conditionally disable debug toolbar for API requests to reduce payload.
    """

    API_PATHS = ["/api/", "/admin/", "/graphql/"]

    def process_request(self, request):
        # Disable debug toolbar for API requests to reduce overhead
        if any(request.path.startswith(path) for path in self.API_PATHS):
            request.META["HTTP_DISABLE_DEBUG_TOOLBAR"] = "true"
        return None
