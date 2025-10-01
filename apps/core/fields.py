# apps/core/fields.py
import os
from urllib.parse import urlparse

import requests
from django.db import models
from django.utils.translation import gettext_lazy as _


class HybridImageField(models.Field):
    """
    A custom field that can handle both local image files and remote image URLs.
    Stores remote URLs as text and local files as ImageField.
    """

    description = _("Hybrid field for local images and remote URLs")

    def __init__(self, *args, **kwargs):
        self.upload_to = kwargs.pop("upload_to", "")
        self.max_length = kwargs.pop("max_length", 500)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.upload_to:
            kwargs["upload_to"] = self.upload_to
        if self.max_length != 500:
            kwargs["max_length"] = self.max_length
        return name, path, args, kwargs

    def get_internal_type(self):
        return "TextField"

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        """Convert value to appropriate Python object."""
        if value is None:
            return value

        # If it's already a HybridImageValue, return it
        if isinstance(value, HybridImageValue):
            return value

        # If it's a string, determine if it's a URL or file path
        if isinstance(value, str):
            if self._is_remote_url(value):
                return HybridImageValue(url=value, is_remote=True)
            else:
                return HybridImageValue(path=value, is_remote=False)

        # If it's a file, treat as local
        if hasattr(value, "file"):
            return HybridImageValue(file=value, is_remote=False)

        return value

    def get_prep_value(self, value):
        """Convert Python object to query value."""
        if value is None:
            return value

        if isinstance(value, HybridImageValue):
            if value.is_remote:
                return value.url
            else:
                return value.path or (value.file.name if value.file else None)

        return value

    def pre_save(self, model_instance, add):
        """Handle value before saving - download remote images if needed."""
        value = getattr(model_instance, self.attname)

        if value is None:
            return value

        if isinstance(value, HybridImageValue) and value.is_remote and value.url:
            # Download remote image and convert to local file
            try:
                response = requests.get(value.url, timeout=10)
                response.raise_for_status()

                # Extract filename from URL
                parsed_url = urlparse(value.url)
                filename = os.path.basename(parsed_url.path) or "downloaded_image.jpg"

                # Create a file-like object from the response content
                from django.core.files.base import ContentFile

                file_content = ContentFile(response.content)

                # Get or create the actual ImageField on the model
                image_field_name = f"{self.name}_file"
                if hasattr(model_instance, image_field_name):
                    image_field = getattr(model_instance, image_field_name)
                    image_field.save(filename, file_content, save=False)

                    # Update the value to use the local file
                    value = HybridImageValue(file=image_field, is_remote=False)
                    setattr(model_instance, self.attname, value)

            except Exception as e:
                # If download fails, keep the URL but log the error
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to download image from {value.url}: {e}")
                # Keep as remote URL

        return self.get_prep_value(value)

    def _is_remote_url(self, value):
        """Check if the value is a remote URL."""
        return isinstance(value, str) and (
            value.startswith("http://") or value.startswith("https://")
        )


class HybridImageValue:
    """Container for hybrid image data."""

    def __init__(self, url=None, path=None, file=None, is_remote=False):
        self.url = url
        self.path = path
        self.file = file
        self.is_remote = is_remote

    def __str__(self):
        if self.is_remote:
            return self.url or ""
        elif self.file:
            return self.file.url if hasattr(self.file, "url") else str(self.file)
        else:
            return self.path or ""

    def __bool__(self):
        return bool(self.url or self.path or self.file)
