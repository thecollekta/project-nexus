# apps/orders/management/commands/cleanup_carts.py

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.orders.models import Cart


class Command(BaseCommand):
    help = "Clean up expired guest carts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Remove carts older than this many days (default: 30)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]

        cutoff_date = timezone.now() - timedelta(days=days)

        # Find expired carts
        expired_carts = Cart.objects.filter(expires_at__lt=timezone.now()).exclude(
            user__isnull=False
        )  # Don't delete user carts

        # Also find old guest carts without expiry dates
        old_guest_carts = Cart.objects.filter(
            user__isnull=True, expires_at__isnull=True, created_at__lt=cutoff_date
        )

        total_carts = expired_carts.count() + old_guest_carts.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {total_carts} expired/old carts"
                )
            )
            self.stdout.write(f"Expired carts: {expired_carts.count()}")
            self.stdout.write(f"Old guest carts: {old_guest_carts.count()}")
        else:
            expired_deleted = expired_carts.delete()[0]
            old_deleted = old_guest_carts.delete()[0]
            total_deleted = expired_deleted + old_deleted

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {total_deleted} expired/old carts"
                )
            )
