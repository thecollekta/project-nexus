# apps/core/graphql.py

import time

import structlog
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from rest_framework_simplejwt.authentication import JWTAuthentication

SENSITIVE_KEYS = {
    "password",
    "password1",
    "password2",
    "new_password",
    "newPassword",
    "new_password_confirm",
    "token",
    "refresh",
    "access",
}


def _mask(value):
    try:
        s = str(value)
    except Exception:
        return "***"
    return "***" if len(s) <= 8 else s[:2] + "***" + s[-2:]


def _sanitize(obj):
    if isinstance(obj, dict):
        return {
            k: (_mask(v) if k in SENSITIVE_KEYS else _sanitize(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


class AuthenticatedGraphQLView(GraphQLView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        try:
            user_auth = JWTAuthentication()
            result = user_auth.authenticate(request)
            if result:
                user, _ = result
                request.user = user
        except Exception as e:
            structlog.get_logger("graphql").warning(
                "jwt_auth_in_graphql_failed",
                error=str(e),
            )
        return super().dispatch(request, *args, **kwargs)

    def execute_graphql_request(
        self,
        request,
        data,
        query,
        variables,
        operation_name,
        show_graphiql=False,
    ):
        logger = structlog.get_logger("graphql")
        start = time.time()

        user = getattr(request, "user", None)
        user_id = (
            str(getattr(user, "id", ""))
            if getattr(user, "is_authenticated", False)
            else None
        )
        username = getattr(user, "username", None) if user_id else None
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[
            0
        ] or request.META.get("REMOTE_ADDR")
        req_id = request.META.get("HTTP_X_REQUEST_ID") or request.META.get(
            "X_REQUEST_ID",
        )

        safe_vars = _sanitize(variables or {})

        logger.info(
            "graphql_request_started",
            operation=operation_name,
            user_id=user_id,
            username=username,
            ip=ip,
            path=request.path,
            method=request.method,
            query_len=len(query or "") if query else 0,
            variables=safe_vars,
            request_id=req_id,
        )

        result = super().execute_graphql_request(
            request,
            data,
            query,
            variables,
            operation_name,
            show_graphiql,
        )

        duration_ms = int((time.time() - start) * 1000)
        errors_count = 0
        if result and getattr(result, "errors", None):
            errors_count = len(result.errors)

        level = "warning" if duration_ms > 1000 or errors_count else "info"
        log_fn = getattr(logger, level)

        log_fn(
            "graphql_request_completed",
            operation=operation_name,
            user_id=user_id,
            username=username,
            ip=ip,
            path=request.path,
            duration_ms=duration_ms,
            errors_count=errors_count,
            request_id=req_id,
        )

        return result
