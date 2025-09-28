# apps/accounts/views.py

"""
User authentication views for the e-commerce API.
Handles user registration, login, profile management, and password operations.
"""

from typing import ClassVar

import structlog
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from drf_spectacular.openapi import OpenApiExample
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts import serializers
from apps.accounts.models import User
from apps.accounts.serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from apps.accounts.tasks import send_verification_email
from apps.core.throttling import CreateAccountRateThrottle, LoginRateThrottle
from apps.core.views import BaseViewSet

logger = structlog.get_logger(__name__)

# HTTP status codes as constants
HTTP_200_OK = status.HTTP_200_OK


class BaseAuthViewMixin:
    """Base mixin for common authentication functionality."""

    def _get_client_info(self, request):
        """Extract client information from request."""
        return {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }

    def _handle_serializer_validation(
        self, request, serializer, success_handler, error_message
    ):
        """Common method to handle serializer validation with error handling."""
        try:
            if serializer.is_valid():
                return success_handler(serializer, request)

            logger.warning(
                f"{error_message}: {serializer.errors}",
                extra={
                    "ip_address": request.META.get("REMOTE_ADDR"),
                    "errors": serializer.errors,
                },
            )

            return Response(
                {
                    "message": _(error_message),
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(
                f"Unexpected error: {e}",
                exc_info=True,
                extra={"ip_address": request.META.get("REMOTE_ADDR")},
            )

            return Response(
                {
                    "message": _("An unexpected error occurred. Please try again."),
                    "error": "operation_failed",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _send_email_notification(self, user, email_type, **kwargs):
        """Send email notifications based on type."""
        email_tasks = {
            "verification": send_verification_email,
        }

        if email_type in email_tasks:
            email_tasks[email_type].delay(user.id)
        elif email_type == "password_reset":
            self._send_password_reset_email(user, **kwargs)


class EmailVerificationMixin:
    """Mixin for email verification functionality."""

    def _verify_email_token(self, uid, token):
        """Verify email token and return user if valid."""
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None

        if not default_token_generator.check_token(user, token):
            return None

        return user


@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        summary="Register a new user account",
        description="""
        Creates a new user account with the provided information.

        ### Flow:
        1. User submits registration data
        2. System validates the input
        3. Account is created in inactive state
        4. Verification email is sent to the provided email address
        5. User must verify email to activate the account

        ### Security:
        - Passwords are hashed using PBKDF2 with SHA-256
        - Email verification required before account activation
        - Rate limited to prevent abuse
        """,
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                response=UserRegistrationSerializer,
                description="User created successfully",
                examples=[
                    OpenApiExample(
                        "Registration Success",
                        value={
                            "message": "Account created successfully. Please check your email to verify your account.",
                            "user": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "username": "kwame.nkrumah",
                                "email": "user@example.com",
                                "full_name": "Kwame Nkrumah",
                            },
                            "next_step": "email_verification",
                        },
                        description="Successful registration response",
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Validation errors",
                examples=[
                    OpenApiExample(
                        "Validation Error - Email Exists",
                        value={
                            "email": ["user with this email already exists."],
                        },
                    ),
                    OpenApiExample(
                        "Validation Error - Password Mismatch",
                        value={
                            "password_confirm": ["Passwords do not match."],
                        },
                    ),
                    OpenApiExample(
                        "Validation Error - Terms Not Accepted",
                        value={
                            "accept_terms": [
                                "You must accept the terms and conditions.",
                            ],
                        },
                    ),
                ],
            ),
            429: OpenApiResponse(
                description="Too many registration attempts",
                examples=[
                    OpenApiExample(
                        "Rate Limited",
                        value={
                            "detail": "Request was throttled. Expected available in 60 seconds.",
                        },
                    ),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Registration Request Example",
                value={
                    "username": "Kwams",
                    "email": "kwame.nkrumah@ghana.com",
                    "password": "Blackstar233.",
                    "password_confirm": "Blackstar233.",
                    "first_name": "Kwame",
                    "last_name": "Nkrumah",
                    "phone_number": "+2332498051198",
                    "address_line_1": "Black Star Square",
                    "address_line_2": "Opposite Accra Sports Stadium",
                    "city": "Accra",
                    "state": "Greater Accra",
                    "postal_code": "0233",
                    "country": "Ghana",
                    "accept_terms": True,
                },
                request_only=True,
            ),
        ],
    ),
)
class UserRegistrationView(APIView, BaseAuthViewMixin):
    """
    API endpoint for user registration.

    This endpoint allows new users to create an account in the system.
    After successful registration, an email with a verification link is sent to the user's email address.
    The user must verify their email before they can log in.

    ### Required Fields:
    - `email`: A valid email address (must be unique)
    - `password`: Password (min 8 characters)
    - `password_confirm`: Must match the password field
    - `accept_terms`: Must be set to `true`

    ### Optional Fields:
    - `first_name`: User's first name
    - `last_name`: User's last name
    - `phone_number`: Contact number (international format: +233XXXXXXXXX)
    - `address_line_1`: Primary address
    - `city`: City
    - `country`: Country

    ### Response:
    - `201 Created`: User registered successfully
    - `400 Bad Request`: Validation error
    - `429 Too Many Requests`: Rate limit exceeded
    """

    permission_classes: ClassVar[list[type[permissions.BasePermission]]] = [
        permissions.AllowAny,
    ]
    throttle_classes: ClassVar[list[type[object]]] = [CreateAccountRateThrottle]
    serializer_class: type[UserRegistrationSerializer] = UserRegistrationSerializer

    def post(self, request):
        """
        Register a new user account.

        Returns:
        - 201: User created successfully
        - 400: Validation errors
        - 429: Too many registration attempts
        """

        def success_handler(serializer, request):
            user = serializer.save()

            # Log successful registration
            logger.info(
                f"New user registered: {user.username}",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                    **self._get_client_info(request),
                },
            )

            # Return success response without sensitive data
            response_data = {
                "message": "Account created successfully. Please check your email to verify your account.",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                },
                "next_step": "email_verification",
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        serializer = UserRegistrationSerializer(data=request.data)
        return self._handle_serializer_validation(
            request,
            serializer,
            success_handler,
            "Registration failed. Please check the errors below.",
        )


class UserLoginView(APIView, BaseAuthViewMixin):
    """
    API view for user login with JWT token generation.
    Supports username or email login.
    """

    permission_classes: ClassVar[list[type[permissions.BasePermission]]] = [
        permissions.AllowAny,
    ]
    throttle_classes: ClassVar[list[type[object]]] = [LoginRateThrottle]
    serializer_class: type[UserLoginSerializer] = UserLoginSerializer

    @extend_schema(
        tags=["Authentication"],
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Login successful",
                examples=[
                    OpenApiExample(
                        "Login Success",
                        value={
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "user": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "username": "kwame.nkrumah",
                                "email": "user@example.com",
                                "first_name": "Kwame",
                                "last_name": "Nkrumah",
                            },
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(description="Invalid credentials"),
            429: OpenApiResponse(description="Too many login attempts"),
        },
        summary="User login",
    )
    def post(self, request):
        """
        Authenticate user and return JWT tokens.

        Returns:
        - 200: Login successful with tokens
        - 400: Invalid credentials or validation errors
        - 429: Too many login attempts
        """
        try:
            serializer = self.serializer_class(
                data=request.data,
                context={"request": request},
            )
            if not serializer.is_valid():
                return Response(
                    {"non_field_errors": ["Invalid email or password."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get the response data from the serializer
            response_data = serializer.validated_data

            # Log successful login
            user = User.objects.get(email=request.data.get("email"))
            logger.info(
                f"User logged in: {user.username}",
                extra={
                    "user_id": str(user.id),
                    **self._get_client_info(request),
                },
            )

            return Response(response_data, status=status.HTTP_200_OK)

        except (User.DoesNotExist, serializers.ValidationError) as e:
            logger.warning(
                "Login failed",
                extra={"error": str(e), **self._get_client_info(request)},
            )
            return Response(
                {"non_field_errors": ["Invalid email or password."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(
                "Unexpected error during login",
                extra={"error": str(e), **self._get_client_info(request)},
                exc_info=True,
            )
            return Response(
                {"error": "An error occurred during login"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserLogoutView(APIView, BaseAuthViewMixin):
    """
    API view for user logout.
    Blacklists the refresh token to prevent reuse.
    """

    permission_classes: ClassVar[list[type[permissions.BasePermission]]] = [
        permissions.IsAuthenticated,
    ]

    @extend_schema(
        tags=["Authentication"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "refresh": {
                        "type": "string",
                        "description": "Refresh token to blacklist",
                    },
                },
                "required": ["refresh"],
                "example": {"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
            },
        },
        responses={
            205: OpenApiResponse(
                description="Successfully logged out",
                examples=[
                    OpenApiExample(
                        "Logout Success",
                        value={"detail": "Successfully logged out."},
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Invalid request or token",
                examples=[
                    OpenApiExample(
                        "Invalid Token",
                        value={"detail": "Refresh token is required."},
                    ),
                ],
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided",
            ),
        },
        description="Logout user by blacklisting the refresh token. This will invalidate the token and prevent its future use.",
        summary="User logout",
    )
    def post(self, request):
        """
        Logout user by blacklisting refresh token.
        """
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            # Log the logout
            logger.info(
                "User logged out successfully",
                user_id=str(request.user.id),
                username=request.user.username,
                **self._get_client_info(request),
            )

            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT,
            )

        except Exception as e:
            logger.error(
                "Logout failed",
                error=str(e),
                user_id=str(request.user.id) if request.user.is_authenticated else None,
            )
            return Response(
                {"detail": "Invalid token or token expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BaseUserActionMixin:
    """Mixin for common user actions."""

    def _set_user_active_status(self, request, user_id, activate=True):
        """Common method to activate/deactivate users."""
        user = self.get_object()
        action_word = "active" if activate else "inactive"

        if user.is_active == activate:
            return Response(
                {"detail": f"User is already {action_word}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = activate
        user.save(update_fields=["is_active", "updated_at"])

        logger.info(
            f"User account {action_word} by admin: {user.email}",
            extra={
                "admin_id": str(request.user.id),
                "user_id": str(user.id),
                **self._get_client_info(request),
            },
        )

        return Response(
            {"detail": f"User account {action_word}d successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["User Profile Management (Admin Only)"])
class AdminUserViewSet(BaseViewSet, BaseUserActionMixin, BaseAuthViewMixin):
    """
    Admin-only ViewSet for user management.
    Provides CRUD operations for managing users (admin only).
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()
    lookup_field = "id"
    lookup_url_kwarg = "id"

    @extend_schema(
        methods=["POST"],
        summary="Activate user account",
        description="Activate a user account (admin only)",
        responses={
            200: OpenApiResponse(description="User activated successfully"),
            400: OpenApiResponse(description="User is already active"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
            404: OpenApiResponse(description="User not found"),
        },
    )
    @action(detail=True, methods=["post"], url_path="activate")
    def activate_user(self, request, user_id=None):
        """Activate a user account (admin only)."""
        return self._set_user_active_status(request, user_id, activate=True)

    @extend_schema(
        methods=["POST"],
        summary="Deactivate user account",
        description="Deactivate a user account (admin only)",
        responses={
            200: OpenApiResponse(description="User deactivated successfully"),
            400: OpenApiResponse(description="User is already inactive"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Admin permission required"),
            404: OpenApiResponse(description="User not found"),
        },
    )
    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate_user(self, request, user_id=None):
        """Deactivate a user account (admin only)."""
        return self._set_user_active_status(request, user_id, activate=False)


class PasswordManagementMixin(BaseAuthViewMixin):
    """Mixin for password management functionality."""

    def _invalidate_user_tokens(self, user):
        """Invalidate all user's refresh tokens."""
        tokens = OutstandingToken.objects.filter(user=user)
        for token in tokens:
            try:
                refresh = RefreshToken(token.token)
                refresh.blacklist()
                BlacklistedToken.objects.get_or_create(token=token)
            except Exception as e:
                logger.warning(f"Failed to blacklist token: {e}")
                continue

    def _send_password_reset_email(self, user):
        """Send password reset email."""
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Build reset URL (frontend URL)
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

        # Email subject and message
        subject = "Password Reset Request"
        message = render_to_string(
            "emails/password_reset_email.html",
            {
                "user": user,
                "reset_url": reset_url,
                "site_name": settings.SITE_NAME,
            },
        )

        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=message,
            fail_silently=False,
        )


@extend_schema(tags=["User Profile"])
class UserProfileViewSet(
    BaseViewSet, PasswordManagementMixin, EmailVerificationMixin, BaseAuthViewMixin
):
    """
    ViewSet for user profile management.
    Provides CRUD operations for user profiles with proper permissions.
    """

    serializer_class: type[UserProfileSerializer] = UserProfileSerializer
    permission_classes: ClassVar[list[type[permissions.BasePermission]]] = [
        permissions.IsAuthenticated,
    ]
    queryset = User.objects.none()

    def check_object_permissions(self, request, obj):
        """Ensure users can only access their own profile."""
        super().check_object_permissions(request, obj)
        if obj != request.user:
            self.permission_denied(
                request,
                message="You do not have permission to perform this action.",
                code=status.HTTP_403_FORBIDDEN,
            )

    def get_queryset(self):
        """
        Return queryset based on user permissions.
        Regular users can only see their own profile.
        """
        # For OpenAPI schema generation
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()

        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    def create(self, request, *args, **kwargs):
        """
        Prevent profile creation through this endpoint.
        Profiles are created automatically during user registration.
        """
        return Response(
            {
                "message": _(
                    "Profile creation is not allowed through this endpoint. "
                    "Please use the registration endpoint at /api/v1/accounts/register/",
                ),
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_object(self):
        """
        Handle 'me' lookup for current user profile.
        """
        if self.kwargs.get("pk") == "me":
            return self.request.user
        return super().get_object()

    def update(self, request, *args, **kwargs):
        """
        Handle PUT requests for user profile updates.
        """
        if kwargs.get("pk") == "me":
            return self.update_me(request)
        # For non-me updates, use standard behavior
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Handle PATCH requests for user profile updates."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Log the profile update
        logger.info(
            f"Profile updated for user: {instance.username}",
            extra={
                "user_id": str(instance.id),
                **self._get_client_info(request),
                "updated_fields": list(request.data.keys()),
            },
        )

        return Response(serializer.data)

    @extend_schema(
        methods=["GET"],
        summary="Get current user profile",
        description="Retrieve the currently authenticated user's profile.",
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(
                description="Authentication credentials were not provided",
            ),
        },
    )
    @action(detail=False, methods=["get"])
    def me(self, request):
        """
        Get current user's profile.
        """
        try:
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching user profile: {e}")
            return Response(
                {"message": _("Error fetching profile data")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        methods=["PUT", "PATCH"],
        summary="Update current user profile",
        description="Update the currently authenticated user's profile.",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            401: OpenApiResponse(
                description="Authentication credentials were not provided",
            ),
        },
    )
    @action(detail=False, methods=["put", "patch"], url_path="me")
    def update_me(self, request):
        """
        Update current user's profile via /me/ endpoint.
        """
        try:
            user = request.user
            serializer = self.get_serializer(
                user,
                data=request.data,
                partial=request.method == "PATCH",
            )

            if serializer.is_valid():
                serializer.save()

                logger.info(
                    f"Profile updated for user: {user.username}",
                    extra={"user_id": str(user.id)},
                )

                return Response(
                    {
                        "message": _("Profile updated successfully"),
                        "user": serializer.data,
                    },
                )

            return Response(
                {
                    "message": _("Profile update failed"),
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return Response(
                {"message": _("An error occurred while updating profile")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        methods=["POST"],
        summary="Change password",
        description="Change the current user's password.",
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(
                description="Password changed successfully",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={"detail": "Password updated successfully"},
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Invalid input",
                examples=[
                    OpenApiExample(
                        "Error",
                        value={
                            "detail": "Password change failed",
                            "errors": {
                                "old_password": ["Current password is incorrect"],
                            },
                        },
                    ),
                ],
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided",
            ),
        },
    )
    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        """
        Change user password.

        Required fields in request body:
        - old_password: Current password
        - new_password: New password (min 8 characters)
        - new_password_confirm: Confirmation of new password

        Returns:
        - 200: Password changed successfully
        - 400: Validation errors or invalid input
        - 500: Server error
        """
        try:
            serializer = PasswordChangeSerializer(
                data=request.data,
                context={"request": request},
            )

            if not serializer.is_valid():
                return Response(
                    {
                        "message": _(
                            "Password change failed. Please check the errors below.",
                        ),
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Change the password
            user = request.user
            user.set_password(serializer.validated_data["new_password"])
            user.save()

            # Log the password change
            logger.info(
                f"Password changed for user: {user.username}",
                extra={
                    "user_id": str(user.id),
                    **self._get_client_info(request),
                },
            )

            # Invalidate all user's refresh tokens
            self._invalidate_user_tokens(user)

            return Response(
                {
                    "message": _("Password changed successfully."),
                    "next_steps": [
                        _("You have been logged out of all other devices."),
                        _("Please log in again with your new password."),
                    ],
                },
            )

        except Exception as e:
            logger.error(
                f"Error changing password for user {request.user.id}: {e!s}",
                exc_info=True,
                extra={
                    "user_id": str(request.user.id),
                    **self._get_client_info(request),
                },
            )
            return Response(
                {
                    "message": _(
                        "An error occurred while changing password. Please try again later.",
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        methods=["POST"],
        summary="Request verification email",
        description="Request a verification email to be sent to the user's email address.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "Email address to send verification to (optional - uses authenticated user's email if not provided)",
                        "example": "user@example.com",
                    },
                },
                "required": [],
            },
        },
        responses={
            200: OpenApiResponse(
                description="Verification email sent successfully",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={"message": "Verification email sent successfully"},
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Email already verified",
                examples=[
                    OpenApiExample(
                        "Error",
                        value={"message": "Email is already verified"},
                    ),
                ],
            ),
        },
    )
    @action(detail=False, methods=["post"], url_path="verify-email")
    def request_verification_email(self, request):
        """
        Request verification email to be sent.
        """
        try:
            email = request.data.get("email")

            if not email and request.user.is_authenticated:
                user = request.user
                email = user.email  # Use the authenticated user's email
            else:
                try:
                    user = User.objects.get(email__iexact=email)
                except User.DoesNotExist:
                    # Return 200 to prevent email enumeration
                    return Response(
                        {
                            "message": _(
                                "If your email is registered, you will receive a verification email.",
                            ),
                        },
                        status=status.HTTP_200_OK,
                    )

            if user.email_verified:
                return Response(
                    {"message": _("Email is already verified.")},
                    status=status.HTTP_200_OK,  # Changed from 400 to 200
                )

            # Generate and save verification token
            user.generate_email_verification_token()
            user.save()

            # Send verification email
            send_verification_email.delay(user.id)

            logger.info(
                f"Verification email requested for user: {user.email}",
                extra={"user_id": str(user.id)},
            )

            return Response(
                {"message": _("Verification email sent successfully")},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error requesting verification email: {e}", exc_info=True)
            return Response(
                {"message": _("An error occurred while requesting verification email")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        methods=["POST"],
        summary="Verify email",
        description="Verify user's email address with token and UID.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "description": "Email verification token sent to the user's email",
                        "example": "iNKR2qKEdVdWS5852xYXuDxUGuFz37qyNVSBCc2g0MnljsaP4MdDCpViNKr4CEjh",
                    },
                    "uid": {
                        "type": "string",
                        "description": "User ID encoded in the verification link",
                        "example": "MjU1ZTg0MDBlLTI5YjQtNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMA",
                    },
                },
                "required": ["token", "uid"],
            },
        },
        responses={
            200: OpenApiResponse(
                description="Email verified successfully",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "message": "Email verified successfully. Your account is now active.",
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Invalid or expired token",
                examples=[
                    OpenApiExample(
                        "Error",
                        value={"message": "Invalid verification token"},
                    ),
                ],
            ),
        },
    )
    @action(detail=False, methods=["post"], url_path="verify-email/confirm")
    def verify_email(self, request):
        """
        Verify user email address with token.
        """
        try:
            token = request.data.get("token")
            uid = request.data.get("uid")

            if not token or not uid:
                return Response(
                    {"message": _("Token and UID are required")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = self._verify_email_token(uid, token)
            if user is None:
                return Response(
                    {"message": _("Invalid or expired verification link")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if user.email_verified:
                return Response(
                    {"message": _("Email is already verified")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Mark email as verified
            user.email_verified = True
            user.save()

            logger.info(
                f"Email verified for user: {user.email}",
                extra={"user_id": str(user.id)},
            )

            return Response(
                {"message": _("Email verified successfully")},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error verifying email: {e}", exc_info=True)
            return Response(
                {"message": _("An error occurred while verifying email")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        methods=["POST"],
        summary="Request password reset",
        description="Request a password reset email to be sent to the provided email address.",
        request=PasswordResetSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset email sent if account exists",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "message": "If the email exists in our system, you will receive password reset instructions.",
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Invalid input",
                examples=[
                    OpenApiExample(
                        "Error",
                        value={"email": ["This field is required."]},
                    ),
                ],
            ),
        },
    )
    @action(detail=False, methods=["post"], url_path="request-password-reset")
    def request_password_reset(self, request):
        """
        Request password reset email.

        This endpoint initiates the password reset process by sending an email
        with a reset link to the provided email address if it exists in the system.
        For security reasons, the response does not indicate whether the email exists.
        """
        try:
            serializer = PasswordResetSerializer(data=request.data)

            if serializer.is_valid():
                email = serializer.validated_data["email"]

                try:
                    user = User.objects.get(email__iexact=email)
                    self._send_password_reset_email(user)

                    logger.info(
                        f"Password reset requested for: {email}",
                        extra={"user_id": str(user.id)},
                    )

                except User.DoesNotExist:
                    # Log the attempt but don't reveal if email exists
                    logger.warning(
                        f"Password reset requested for non-existent email: {email}",
                        extra={"ip_address": request.META.get("REMOTE_ADDR")},
                    )

                # Always return success message for security
                return Response(
                    {
                        "message": _(
                            "If the email exists in our system, you will receive password reset instructions.",
                        ),
                    },
                )

            return Response(
                {
                    "message": _("Invalid email address"),
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(f"Error processing password reset: {e}", exc_info=True)
            return Response(
                {"message": _("An error occurred. Please try again later.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        methods=["POST"],
        summary="Confirm password reset",
        description="Set a new password using uid and token from the reset email.",
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description="Password reset successful")},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="reset-password/confirm",
        permission_classes=[permissions.AllowAny],
    )
    def reset_password_confirm(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": _("Invalid input"), "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except Exception:
            return Response(
                {"message": _("Invalid reset link")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {"message": _("Invalid or expired reset token")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        return Response(
            {"message": _("Password has been reset successfully")},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Authentication"],
    summary="Refresh JWT access token",
    description="""
    Refresh an expired access token using a valid refresh token.

    This endpoint allows users to obtain a new access token when their current one has expired,
    without requiring them to log in again. The refresh token must be valid and not blacklisted.
    """,
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "refresh": {
                    "type": "string",
                    "description": "The refresh token issued during login",
                    "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                },
            },
            "required": ["refresh"],
        },
    },
    responses={
        200: OpenApiResponse(
            response={
                "type": "object",
                "properties": {
                    "access": {
                        "type": "string",
                        "description": "New JWT access token",
                        "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    },
                    "access_expiration": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Expiration datetime of the new access token",
                        "example": "2023-09-15T18:30:00+00:00",
                    },
                },
            },
            description="Token refreshed successfully",
        ),
        400: OpenApiResponse(
            response={
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "example": "Token is invalid or expired",
                    },
                    "code": {
                        "type": "string",
                        "example": "token_not_valid",
                    },
                },
            },
            description="Invalid or expired refresh token",
        ),
        401: OpenApiResponse(
            response={
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "example": "No valid token found in the header",
                    },
                    "code": {
                        "type": "string",
                        "example": "no_authorization",
                    },
                },
            },
            description="No authentication credentials provided",
        ),
    },
)
class CustomTokenRefreshView(TokenRefreshView, BaseAuthViewMixin):
    """
    Custom token refresh view with additional logging.
    """

    @extend_schema(
        operation_id="refresh_token",
        description="""
        Refresh the authentication token using a valid refresh token.

        This endpoint allows users to obtain a new access token when their current one has expired,
        without requiring them to log in again. The refresh token must be valid and not blacklisted.
        """,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                    "access_expiration": {"type": "string", "format": "date-time"},
                },
            },
            400: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                    "code": {"type": "string"},
                },
            },
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Refresh authentication token.

        This endpoint accepts a refresh token and returns a new access token if the refresh token is valid.
        The refresh token must be included in the request body.

        Returns:
        - 200: New access token and its expiration time
        - 400: Invalid or expired refresh token
        - 401: No authentication credentials provided
        """
        response = super().post(request, *args, **kwargs)

        if response.status_code == HTTP_200_OK:
            logger.info(
                "Token refreshed successfully",
                extra={"ip_address": request.META.get("REMOTE_ADDR")},
            )

        return response
