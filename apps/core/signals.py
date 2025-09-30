# apps/core/signals.py

import structlog
from django.dispatch import receiver
from rest_framework.throttling import rate_limit_exceeded

logger = structlog.get_logger(__name__)


@receiver(rate_limit_exceeded)
def log_rate_limit_exceeded(sender, request, **kwargs):
    """Log rate limit exceeded events."""
    client_ip = request.META.get("REMOTE_ADDR", "unknown")
    user = getattr(request, "user", None)
    user_id = user.id if user and user.is_authenticated else "anonymous"
    operation = getattr(request, "operation_name", "unknown")

    logger.warning(
        f"Rate limit exceeded - IP: {client_ip}, User: {user_id}, Operation: {operation}"
    )

    # TODO send an alert or increment a metric here
