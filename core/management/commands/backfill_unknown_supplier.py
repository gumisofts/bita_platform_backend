from django.core.management.base import BaseCommand
from django.db import transaction

from business.models import Business
from inventories.models import Supplier


class Command(BaseCommand):
    help = (
        "Create a default 'Unknown' Supplier for every business that does not "
        "already have one. Safe to re-run — businesses that already have an "
        "'Unknown' supplier are skipped."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview which businesses would be affected without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        businesses_missing = Business.objects.exclude(
            supplier__name="Unknown"
        ).distinct()

        total = businesses_missing.count()

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "All businesses already have an 'Unknown' supplier. Nothing to do."
                )
            )
            return

        self.stdout.write(
            f"Found {total} business(es) missing an 'Unknown' supplier:\n"
        )

        created = 0

        with transaction.atomic():
            for business in businesses_missing:
                self.stdout.write(f"  [{business.pk}] {business.name}")

                if not dry_run:
                    Supplier.objects.create(name="Unknown", business=business)
                    created += 1

            if dry_run:
                transaction.set_rollback(True)

        label = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{label} 'Unknown' supplier for {total if dry_run else created} business(es)."
            )
        )
