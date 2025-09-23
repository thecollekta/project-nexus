# ecommerce_backend/schema.py

from contextlib import suppress

import graphene
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from graphene_django import DjangoObjectType

from apps.accounts.serializers import (
    EmailVerificationSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from apps.accounts.tasks import send_verification_email
from apps.products.schema import Mutation as ProductsMutation
from apps.products.schema import Query as ProductsQuery

User = get_user_model()


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "email_verified",
            "user_type",
            "account_status",
            "date_joined",
            "last_login",
        )


class Query(ProductsQuery, graphene.ObjectType):
    me = graphene.Field(UserType, description="Current authenticated user profile")
    users = graphene.List(
        UserType,
        description="List all users (admin only)",
    )

    def resolve_me(self, info):
        user = info.context.user
        if not user or not user.is_authenticated:
            return None
        return user

    def resolve_users(self, info):
        user = info.context.user
        if not user or not user.is_authenticated or not user.is_staff:
            msg = "Admin permission required"
            raise PermissionDenied(msg)
        return User.objects.all()


class RegisterUser(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        password_confirm = graphene.String(required=True)
        first_name = graphene.String(required=False)
        last_name = graphene.String(required=False)
        phone_number = graphene.String(required=False)
        address_line_1 = graphene.String(required=False)
        address_line_2 = graphene.String(required=False)
        city = graphene.String(required=False)
        state = graphene.String(required=False)
        postal_code = graphene.String(required=False)
        country = graphene.String(required=False)
        accept_terms = graphene.Boolean(required=True)

    ok = graphene.Boolean()
    user = graphene.Field(UserType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, **kwargs):
        serializer = UserRegistrationSerializer(
            data=kwargs,
            context={"request": info.context},
        )
        if serializer.is_valid():
            user = serializer.save()
            with suppress(Exception):
                send_verification_email.delay(user.id)
            return RegisterUser(ok=True, user=user, errors=[])
        errors = []
        for field, msgs in serializer.errors.items():
            if isinstance(msgs, (list, tuple)):
                for m in msgs:
                    errors.append(f"{field}: {m}")
            else:
                errors.append(f"{field}: {msgs}")
        return RegisterUser(ok=False, user=None, errors=errors)


class Login(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        remember_me = graphene.Boolean(required=False, default_value=False)

    ok = graphene.Boolean()
    access = graphene.String()
    refresh = graphene.String()
    user = graphene.Field(UserType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, email, password, remember_me=False):
        serializer = UserLoginSerializer(
            data={"email": email, "password": password, "remember_me": remember_me},
            context={"request": info.context},
        )
        if serializer.is_valid():
            data = serializer.validated_data
            # Return the user after login only if session auth is established; otherwise omit
            user = (
                info.context.user
                if getattr(info.context, "user", None)
                and info.context.user.is_authenticated
                else None
            )
            return Login(
                ok=True,
                access=data.get("access"),
                refresh=data.get("refresh"),
                user=user,
                errors=[],
            )
        errors = []
        for field, msgs in serializer.errors.items():
            if isinstance(msgs, (list, tuple)):
                for m in msgs:
                    errors.append(f"{field}: {m}")
            else:
                errors.append(f"{field}: {msgs}")
        return Login(ok=False, access=None, refresh=None, user=None, errors=errors)


class UpdateProfile(graphene.Mutation):
    class Arguments:
        first_name = graphene.String(required=False)
        last_name = graphene.String(required=False)
        phone_number = graphene.String(required=False)
        address_line_1 = graphene.String(required=False)
        address_line_2 = graphene.String(required=False)
        city = graphene.String(required=False)
        state = graphene.String(required=False)
        postal_code = graphene.String(required=False)
        country = graphene.String(required=False)
        bio = graphene.String(required=False)
        date_of_birth = graphene.String(required=False)
        newsletter_subscription = graphene.Boolean(required=False)

    ok = graphene.Boolean()
    user = graphene.Field(UserType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, **kwargs):
        user = info.context.user
        if not user or not user.is_authenticated:
            msg = "Authentication required"
            raise PermissionDenied(msg)
        serializer = UserProfileSerializer(
            user,
            data=kwargs,
            partial=True,
            context={"request": info.context},
        )
        if serializer.is_valid():
            serializer.save()
            return UpdateProfile(ok=True, user=user, errors=[])
        errors = []
        for field, msgs in serializer.errors.items():
            if isinstance(msgs, (list, tuple)):
                for m in msgs:
                    errors.append(f"{field}: {m}")
            else:
                errors.append(f"{field}: {msgs}")
        return UpdateProfile(ok=False, user=None, errors=errors)


class ChangePassword(graphene.Mutation):
    class Arguments:
        old_password = graphene.String(required=True)
        new_password = graphene.String(required=True)
        new_password_confirm = graphene.String(required=True)

    ok = graphene.Boolean()
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, old_password, new_password, new_password_confirm):
        user = info.context.user
        if not user or not user.is_authenticated:
            msg = "Authentication required"
            raise PermissionDenied(msg)
        serializer = PasswordChangeSerializer(
            data={
                "old_password": old_password,
                "new_password": new_password,
                "new_password_confirm": new_password_confirm,
            },
            context={"request": info.context},
        )
        if serializer.is_valid():
            serializer.save()
            return ChangePassword(
                ok=True,
                message="Password changed successfully.",
                errors=[],
            )
        errors = []
        for field, msgs in serializer.errors.items():
            if isinstance(msgs, (list, tuple)):
                for m in msgs:
                    errors.append(f"{field}: {m}")
            else:
                errors.append(f"{field}: {msgs}")
        return ChangePassword(ok=False, message=None, errors=errors)


class RequestVerificationEmail(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=False)

    ok = graphene.Boolean()
    message = graphene.String()

    @staticmethod
    def mutate(root, info, email=None):
        user = None
        request_user = getattr(info.context, "user", None)
        if not email and request_user and request_user.is_authenticated:
            user = request_user
        elif email:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                # Do not reveal if email exists
                return RequestVerificationEmail(
                    ok=True,
                    message="If your email is registered, you will receive a verification email.",
                )
        else:
            return RequestVerificationEmail(
                ok=True,
                message="If your email is registered, you will receive a verification email.",
            )

        if user.email_verified:
            return RequestVerificationEmail(
                ok=True,
                message="Email is already verified.",
            )

        # Optionally maintain token state; task generates the usable link token
        with suppress(Exception):
            if hasattr(user, "generate_email_verification_token"):
                user.generate_email_verification_token()
                user.save(
                    update_fields=[
                        "email_verification_token",
                        "email_verification_token_created_at",
                        "updated_at",
                    ],
                )
        with suppress(Exception):
            send_verification_email.delay(user.id)

        return RequestVerificationEmail(
            ok=True,
            message="Verification email sent successfully.",
        )


class VerifyEmail(graphene.Mutation):
    class Arguments:
        uid = graphene.String(required=True)
        token = graphene.String(required=True)

    ok = graphene.Boolean()
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, uid, token):
        serializer = EmailVerificationSerializer(data={"uid": uid, "token": token})
        if serializer.is_valid():
            serializer.save()
            return VerifyEmail(
                ok=True,
                message="Email verified successfully.",
                errors=[],
            )
        errors = []
        for field, msgs in serializer.errors.items():
            if isinstance(msgs, (list, tuple)):
                for m in msgs:
                    errors.append(f"{field}: {m}")
            else:
                errors.append(f"{field}: {msgs}")
        return VerifyEmail(ok=False, message=None, errors=errors)


class RequestPasswordReset(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()
    message = graphene.String()

    @staticmethod
    def mutate(root, info, email):
        serializer = PasswordResetSerializer(data={"email": email})
        if not serializer.is_valid():
            # Same generic response to avoid enumeration
            return RequestPasswordReset(
                ok=True,
                message="If the email exists in our system, you will receive password reset instructions.",
            )
        # Send email if user exists
        try:
            user = User.objects.get(email__iexact=serializer.validated_data["email"])
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
            subject = "Password Reset Request"
            message = render_to_string(
                "emails/password_reset_email.html",
                {
                    "user": user,
                    "reset_url": reset_url,
                    "site_name": settings.SITE_NAME,
                },
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=message,
                fail_silently=True,
            )
        except User.DoesNotExist:
            pass
        return RequestPasswordReset(
            ok=True,
            message="If the email exists in our system, you will receive password reset instructions.",
        )


class ResetPasswordConfirm(graphene.Mutation):
    class Arguments:
        uid = graphene.String(required=True)
        token = graphene.String(required=True)
        new_password = graphene.String(required=True)

    ok = graphene.Boolean()
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, uid, token, new_password):
        pwd_serializer = PasswordResetConfirmSerializer(
            data={"uid": uid, "token": token, "new_password": new_password},
        )
        if not pwd_serializer.is_valid():
            errors = []
            for field, msgs in pwd_serializer.errors.items():
                if isinstance(msgs, (list, tuple)):
                    for m in msgs:
                        errors.append(f"{field}: {m}")
                else:
                    errors.append(f"{field}: {msgs}")
            return ResetPasswordConfirm(ok=False, message=None, errors=errors)
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except Exception:
            return ResetPasswordConfirm(
                ok=False,
                message=None,
                errors=["uid: Invalid reset link"],
            )
        if not default_token_generator.check_token(user, token):
            return ResetPasswordConfirm(
                ok=False,
                message=None,
                errors=["token: Invalid or expired reset token"],
            )
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        return ResetPasswordConfirm(
            ok=True,
            message="Password has been reset successfully.",
            errors=[],
        )


class Mutation(ProductsMutation, graphene.ObjectType):
    register_user = RegisterUser.Field()
    login = Login.Field()
    update_profile = UpdateProfile.Field()
    change_password = ChangePassword.Field()
    request_verification_email = RequestVerificationEmail.Field()
    verify_email = VerifyEmail.Field()
    request_password_reset = RequestPasswordReset.Field()
    reset_password_confirm = ResetPasswordConfirm.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
