# apps/core/models.py

"""
Base models for the e-commerce application.
Provides common functionality that can be inherited by other models.
"""

import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class AuditStampedModelBase(models.Model):
    """
    Abstract base model that provides audit fields for tracking
    when records are created and updated, and by whom.
    """

    id: models.UUIDField = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this record",
    )

    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True, help_text="When this record was created"
    )

    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True, help_text="When this record was last updated"
    )

    created_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        help_text="User who created this record",
    )

    updated_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        help_text="User who last updated this record",
    )

    is_active: models.BooleanField = models.BooleanField(
        default=True, help_text="Whether this record is active"
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.__class__.__name__} {self.id}"


# Alias for backward compatibility
BaseModel = AuditStampedModelBase


class ActiveManager(models.Manager):
    """
    Custom manager that only returns active (non-soft-deleted) records.
    """

    def get_queryset(self):
        """Override to filter out soft-deleted records by default."""
        return super().get_queryset().filter(is_active=True)


class AllObjectsManager(models.Manager):
    """
    Manager that returns all objects including soft-deleted ones.
    Useful for admin interfaces or data recovery.
    """

    def get_queryset(self):
        """Return all objects regardless of is_active status."""
        return super().get_queryset()


# Example usage in a model:
"""
from apps.core.models import AuditStampedModelBase, ActiveManager, AllObjectsManager

class Product(AuditStampedModelBase):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # Custom managers
    objects = ActiveManager()  # Default manager - only active records
    all_objects = AllObjectsManager()  # All records including deleted

    def __str__(self):
        return self.name
"""
