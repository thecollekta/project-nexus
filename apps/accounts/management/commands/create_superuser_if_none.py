import os
import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError


class Command(BaseCommand):
    help = "Create a superuser if none exists"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.environ.get("SUPERUSER_USERNAME", "admin"),
            help="Superuser username",
        )
        parser.add_argument(
            "--email",
            default=os.environ.get("SUPERUSER_EMAIL", "admin@ecommerce.com"),
            help="Superuser email",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("SUPERUSER_PASSWORD"),
            help="Superuser password (required)",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.SUCCESS("Superuser already exists. Skipping creation.")
            )
            return

        username = options["username"]
        email = options["email"]
        password = options["password"]

        # Validate password
        if not password:
            self.stdout.write(
                self.style.ERROR("SUPERUSER_PASSWORD environment variable not set.")
            )
            self.stdout.write(
                self.style.WARNING(
                    "ℹ Superuser creation skipped. You can create one later."
                )
            )
            return

        try:
            # Create superuser
            User.objects.create_superuser(  # type: ignore
                username=username, email=email, password=password
            )

            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" created successfully')
            )
            self.stdout.write(self.style.SUCCESS(f"Email: {email}"))

        except IntegrityError:
            self.stdout.write(self.style.ERROR(f'User "{username}" already exists.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating superuser: {e}"))
            sys.exit(1)
