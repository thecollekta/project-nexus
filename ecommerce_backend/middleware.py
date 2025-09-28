# ecommerce_backend/middleware.py

from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin


class AuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(request, "user"):
            request.user = AnonymousUser()
        return None
