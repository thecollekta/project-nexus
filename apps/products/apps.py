# apps/products/apps.py

import os
import sys
from threading import Lock

import structlog
from django.apps import AppConfig
from django.conf import settings
from django.core.management import call_command
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

logger = structlog.get_logger(__name__)


class SampleDataPopulator:
    """Thread-safe singleton for managing sample data population state."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if not self.initialized:
            self.population_completed = False
            self.population_lock = Lock()
            self.initialized = True

    @property
    def is_completed(self):
        """Check if population has been completed."""
        return self.population_completed

    def mark_completed(self):
        """Mark population as completed."""
        with self.population_lock:
            self.population_completed = True

    def should_populate(self):
        """Check if population should proceed (thread-safe)."""
        with self.population_lock:
            return not self.population_completed


class ProductsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.products"
    label = "products"
    verbose_name = _("Products")

    def ready(self):
        """Import signals when the app is ready."""
        # Import signals here to avoid circular imports
        try:
            import apps.products.signals  # noqa: F401, PLC0415
        except ImportError:
            logger.warning("Could not import products signals")

        # Connect to post_migrate signal instead of checking database in ready()
        if self._should_setup_auto_populate():
            post_migrate.connect(
                self._handle_post_migrate,
                sender=self,
                dispatch_uid="products_auto_populate",
            )

    def _should_setup_auto_populate(self):
        """Check if we should set up auto-population (no database access)."""
        return all(
            [
                # Only run when starting the development server
                "runserver" in sys.argv,
                # Prevent running twice due to Django's autoreloader
                os.environ.get("RUN_MAIN") != "true",
                # Don't run during tests
                not any(
                    test_cmd in sys.argv
                    for test_cmd in ["test", "test_coverage", "pytest"]
                ),
                # Use django-environ settings (enabled by default)
                getattr(settings, "CREATE_SAMPLE_DATA", True),
                # Now works in both development AND production
                # Remove the environment restriction to allow both dev and prod
            ],
        )

    def _handle_post_migrate(self, sender, **kwargs):
        """Handle post-migration signal to populate sample data."""
        populator = SampleDataPopulator()

        # Only run for our app's migrations
        if sender != self:
            return

        # Check if we should proceed with population
        if not populator.should_populate():
            return

        try:
            if self._database_needs_population():
                self._populate_sample_data()
                populator.mark_completed()
        except Exception as e:
            logger.error(
                "Error during post-migrate sample data population",
                error=str(e),
                exc_info=True,
            )

    def _database_needs_population(self):
        """Check if database needs population (safe to call after migrations)."""
        try:
            # Import here to avoid circular imports during app loading
            from apps.products.models import (
                Category,  # noqa: PLC0415
                Product,  # noqa: PLC0415
            )

            # Check if we should force recreation
            force_recreation = getattr(settings, "FORCE_SAMPLE_DATA_RECREATION", False)

            if force_recreation:
                logger.info("Force recreation enabled, will clear existing data")
                return True

            # Only populate if we have no products or categories
            product_count = Product.objects.count()
            category_count = Category.objects.count()

            needs_population = product_count == 0 or category_count == 0

            # Log with environment context
            current_env = getattr(settings, "ENVIRONMENT", "unknown")
            logger.info(
                "Database population check",
                environment=current_env,
                product_count=product_count,
                category_count=category_count,
                needs_population=needs_population,
            )

            return needs_population

        except Exception as e:
            logger.debug("Could not check database state", error=str(e))
            return False

    def _populate_sample_data(self):
        """Populate the database with sample data."""
        try:
            # Get configuration from django-environ settings
            scenario = getattr(settings, "SAMPLE_DATA_SCENARIO", "demo")
            verbosity = getattr(settings, "SAMPLE_DATA_VERBOSITY", 1)
            admin_user = getattr(settings, "SAMPLE_DATA_ADMIN_USER", "admin")
            force_recreation = getattr(settings, "FORCE_SAMPLE_DATA_RECREATION", False)
            current_env = getattr(settings, "ENVIRONMENT", "unknown")

            logger.info(
                "Starting sample data population",
                environment=current_env,
                scenario=scenario,
                admin_user=admin_user,
                force_recreation=force_recreation,
                verbosity=verbosity,
            )

            # Different scenarios for different environments
            if current_env == "production":
                # Use more conservative settings for production
                scenario = getattr(settings, "SAMPLE_DATA_SCENARIO", "basic")
                logger.warning(
                    "Running sample data population in production",
                    scenario=scenario,
                    environment=current_env,
                )

            # Prepare command arguments
            cmd_args = {
                "scenario": scenario,
                "user": admin_user,
                "verbosity": verbosity,
                "interactive": False,
            }

            # Add clear-existing if force recreation is enabled
            if force_recreation:
                cmd_args["clear_existing"] = True
                logger.warning(
                    "Clearing existing data before population",
                    environment=current_env,
                )

            # Populate sample data
            logger.info(
                "Executing sample data creation command",
                environment=current_env,
            )
            call_command("products_sample_data", **cmd_args)

            # Log successful completion with environment context
            admin_url = getattr(settings, "ADMIN_URL", "admin/")
            logger.info(
                "Sample data population completed successfully",
                environment=current_env,
                admin_url=f"/{admin_url}",
                scenario=scenario,
            )

        except Exception as e:
            current_env = getattr(settings, "ENVIRONMENT", "unknown")
            logger.error(
                "Sample data population failed",
                environment=current_env,
                error=str(e),
                exc_info=True,
            )

    def __str__(self):
        return str(self.verbose_name)
