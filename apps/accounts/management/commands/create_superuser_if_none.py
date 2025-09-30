# apps/accounts/management/commands/

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

        username = options["username"]
        email = options["email"]
        password = options["password"]

        # Check if superuser already exists with this email
        if User.objects.filter(email=email, is_superuser=True).exists():
            self.stdout.write(
                self.style.SUCCESS(f"Superuser with email {email} already exists.")
            )
            return

        # Check if there's a user with admin username but wrong email
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            if user.email != email:
                self.stdout.write(
                    self.style.WARNING(
                        f"User '{username}' exists with email {user.email}. Updating to {email} and making superuser."
                    )
                )
                user.email = email
                user.is_superuser = True
                user.is_staff = True
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated user '{username}' to superuser with email {email}"
                    )
                )
                return

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
            User.objects.create_superuser(
                username=username, email=email, password=password
            )

            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" created successfully')
            )
            self.stdout.write(self.style.SUCCESS(f"Email: {email}"))

        except IntegrityError:
            self.stdout.write(self.style.ERROR(f'User "{username}" already exists.'))
            # Try to update existing user to superuser
            try:
                user = User.objects.get(username=username)
                user.is_superuser = True
                user.is_staff = True
                user.email = email
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated existing user '{username}' to superuser"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating user: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating superuser: {e}"))
            sys.exit(1)
