# apps/core/serializers.py

"""
Base serializers for the e-commerce application.
Provides common serialization functionality for all models.
"""

import html
import re
from typing import Any, ClassVar

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.models import AuditStampedModelBase as BaseModel

User = get_user_model()


class SecurityMixin:
    """
    Mixin that provides security features for serializers.
    Includes input sanitization and basic XSS protection.
    """

    @staticmethod
    def sanitize_input(value: str) -> str:
        """
        Basic input sanitization to prevent XSS attacks.
        Removes potentially dangerous HTML tags and scripts.
        """
        if not isinstance(value, str):
            return value

        # Remove script tags and their content
        value = re.sub(
            r"<script[^>]*>.*?</script>",
            "",
            value,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove potentially dangerous tags
        dangerous_tags = ["script", "iframe", "object", "embed", "form", "input"]
        for tag in dangerous_tags:
            value = re.sub(f"<{tag}[^>]*>", "", value, flags=re.IGNORECASE)
            value = re.sub(f"</{tag}>", "", value, flags=re.IGNORECASE)

        # Escape HTML entities
        value = html.escape(value)

        return value.strip()

    def validate_text_field(self, value: str) -> str:
        """
        Common validation for text fields.
        Sanitizes input and checks for minimum length.
        """
        if value:
            value = self.sanitize_input(value)
            if len(value.strip()) < 1:
                msg = "This field cannot be empty."
                raise serializers.ValidationError(msg)
        return value


class RoleBasedFieldMixin:
    """
    Mixin that provides role-based field visibility and data masking.
    Hides or masks sensitive fields based on user permissions.
    """

    # Define sensitive fields that should be hidden or masked
    sensitive_fields: ClassVar[list[str]] = [
        "created_by",
        "updated_by",
        "is_active",
        "phone_number",
        "email",
        "address_line_1",
        "address_line_2",
        "city",
        "state",
        "postal_code",
        "country",
        "full_address",
    ]

    def mask_sensitive_data(self, field_name: str, value: Any) -> Any:
        """
        Mask sensitive data based on field name.
        """
        if value is None or value == "":
            return value

        if field_name == "phone_number" and isinstance(value, str):
            # Show only last 4 digits of phone number
            return f"*******{value[-4:]}" if len(value) > 4 else "****"

        if field_name == "email" and isinstance(value, str):
            # Mask part of the email (e.g., te**@example.com)
            if "@" in value:
                username, domain = value.split("@")
                if len(username) > 2:
                    masked = username[:2] + "*" * (len(username) - 2)
                    return f"{masked}@{domain}"
                return f"***@{domain}"
            return "***@***"

        # For address fields
        if field_name in [
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "full_address",
        ]:
            return "*****"

        # Default mask for other sensitive fields
        if field_name in self.sensitive_fields:
            if isinstance(value, str):
                return "*" * min(8, len(value)) if value else value
            return "*****"

        return value

    def get_fields(self):
        """
        Override to dynamically show/hide fields based on user role.
        """
        fields = super().get_fields()
        request = self.context.get("request") if hasattr(self, "context") else None

        # If no request context, return all fields without masking
        if not request:
            return fields

        # For authenticated users
        if request.user and request.user.is_authenticated:
            # For non-staff users, mask sensitive fields
            if not request.user.is_staff:
                for field_name in self.sensitive_fields:
                    if field_name in fields:
                        # Only mask if the field is not already read-only
                        if not fields[field_name].read_only:
                            fields[field_name].read_only = True

                        # Add masking in to_representation
                        original_to_rep = fields[field_name].to_representation

                        def make_to_rep(field_name, original_to_rep):
                            def to_rep(value):
                                original_value = (
                                    original_to_rep(value) if original_to_rep else value
                                )
                                return self.mask_sensitive_data(
                                    field_name, original_value
                                )

                            return to_rep

                        fields[field_name].to_representation = make_to_rep(
                            field_name, original_to_rep
                        )

            # For all authenticated users, hide certain audit fields
            audit_fields = ["created_by", "updated_by"]
            for field_name in audit_fields:
                if field_name in fields:
                    fields[field_name].read_only = True

                    # Only show audit fields to staff
                    if not request.user.is_staff:
                        fields[field_name].write_only = True

        # For unauthenticated users, hide sensitive fields completely
        else:
            for field_name in self.sensitive_fields:
                fields.pop(field_name, None)

        return fields

    def to_representation(self, instance):
        """
        Apply masking to sensitive fields in the final representation.
        """
        representation = super().to_representation(instance)
        request = self.context.get("request") if hasattr(self, "context") else None

        # Only apply masking for non-staff users
        if (
            request
            and request.user
            and request.user.is_authenticated
            and not request.user.is_staff
        ):
            for field_name in self.sensitive_fields:
                if field_name in representation:
                    representation[field_name] = self.mask_sensitive_data(
                        field_name, representation[field_name]
                    )

        return representation


class BaseModelSerializer(
    SecurityMixin,
    RoleBasedFieldMixin,
    serializers.ModelSerializer,
):
    """
    Base serializer that provides common functionality for all model serializers.
    Includes security features, audit field handling, and consistent formatting.
    """

    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        # Common fields that should be included in all serializers
        model = BaseModel
        fields: ClassVar[list[str]] = [
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "is_active",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "created_at", "updated_at"]

    def create(self, validated_data: dict[str, Any]) -> BaseModel:
        """
        Create a new instance with the current user as the creator.
        """
        user = self.context.get("request").user if self.context.get("request") else None
        if user and user.is_authenticated:
            validated_data["created_by"] = user
            validated_data["updated_by"] = user
        return super().create(validated_data)

    def update(self, instance: BaseModel, validated_data: dict[str, Any]) -> BaseModel:
        """
        Update an instance with the current user as the last updater.
        """
        user = self.context.get("request").user if self.context.get("request") else None
        if user and user.is_authenticated:
            validated_data["updated_by"] = user
        return super().update(instance, validated_data)

    def to_representation(self, instance: BaseModel) -> dict[str, Any]:
        """
        Customize the representation of the instance.
        """
        representation = super().to_representation(instance)

        # Add user details if they exist
        if instance.created_by:
            representation["created_by"] = str(instance.created_by)
        if instance.updated_by:
            representation["updated_by"] = str(instance.updated_by)

        return representation

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Global validation that applies to all serializers.
        """
        # Sanitize all string fields
        for field_name, value in attrs.items():
            if isinstance(value, str):
                attrs[field_name] = self.sanitize_input(value)

        return super().validate(attrs)


class SanitizedCharField(serializers.CharField):
    """
    Custom CharField that automatically sanitizes input.
    """

    def to_internal_value(self, data: str) -> str:
        """Override to sanitize input automatically."""
        data = super().to_internal_value(data)
        return SecurityMixin.sanitize_input(data)


class SanitizedTextField(serializers.CharField):
    """
    Custom TextField for longer content with enhanced sanitization.
    """

    def to_internal_value(self, data: str) -> str:
        """Override to sanitize input automatically."""
        data = super().to_internal_value(data)
        return SecurityMixin.sanitize_input(data)


# Example usage in a model serializer:
"""
from apps.core.serializers import BaseModelSerializer, SanitizedCharField

class ProductSerializer(BaseModelSerializer):
    name = SanitizedCharField(max_length=255)
    description = SanitizedTextField(required=False)

    class Meta(BaseModelSerializer.Meta):
        model = Product
        fields = BaseModelSerializer.Meta.fields + ['name', 'description', 'price']

    def validate_price(self, value: float) -> float:
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value
"""
