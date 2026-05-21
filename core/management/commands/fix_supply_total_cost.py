from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum

from inventories.models import Supply


class Command(BaseCommand):
    help = (
        "Recalculate Supply.total_cost and Supply.no_of_items using purchase_price. "
        "Run this once to correct records that were populated with selling_price."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        supplies = Supply.objects.prefetch_related("supplied_items").all()
        updated = 0
        skipped = 0

        with transaction.atomic():
            for supply in supplies:
                items = supply.supplied_items.all()

                correct_total_cost = (
                    items.aggregate(
                        total=Sum(
                            ExpressionWrapper(
                                F("quantity") * F("purchase_price"),
                                output_field=DecimalField(),
                            )
                        )
                    )["total"]
                    or 0
                )

                correct_no_of_items = items.count()

                if (
                    supply.total_cost == correct_total_cost
                    and supply.no_of_items == correct_no_of_items
                ):
                    skipped += 1
                    continue

                self.stdout.write(
                    f"  Supply [{supply.label or supply.pk}]  "
                    f"total_cost: {supply.total_cost} → {correct_total_cost}  |  "
                    f"no_of_items: {supply.no_of_items} → {correct_no_of_items}"
                )

                if not dry_run:
                    supply.total_cost = correct_total_cost
                    supply.no_of_items = correct_no_of_items
                    supply.save(update_fields=["total_cost", "no_of_items"])

                updated += 1

            if dry_run:
                transaction.set_rollback(True)

        label = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{label} {updated} supply record(s). Skipped {skipped} already-correct record(s)."
            )
        )
