"""
Sync branch inventory from a customer CSV/Excel export.

Matches existing items by SKU (preferred) or product name, updates corrected
names/fields, sets quantities to the CSV values, and creates missing products.
"""

import csv
import difflib
import io
from collections import OrderedDict
from pathlib import Path

import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from business.models import Branch
from inventories.models import Group, Item, ItemVariant, SuppliedItem, Supply
from inventories.serializers import BULK_IMPORT_COLUMNS


def _parse_int(value, default=0):
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def _parse_decimal(value):
    try:
        parsed = float(str(value).strip())
        return parsed if parsed > 0 else None
    except (ValueError, TypeError):
        return None


def _rows_from_path(file_path: Path):
    """Parse CSV or Excel file into a list of dicts keyed by column name."""
    fname = file_path.name.lower()
    if fname.endswith(".csv"):
        text = file_path.read_text(encoding="utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return [{k.strip(): (v or "") for k, v in row.items()} for row in reader]

    if fname.endswith((".xlsx", ".xls")):
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        raw = list(ws.iter_rows(values_only=True))
        if not raw:
            return []
        headers = [str(h).strip() if h is not None else "" for h in raw[0]]
        return [
            {headers[i]: ("" if v is None else str(v)) for i, v in enumerate(row)}
            for row in raw[1:]
        ]

    raise CommandError("Only CSV (.csv) and Excel (.xlsx / .xls) files are supported.")


def _fuzzy_find_item(branch, product_name, threshold):
    """Return the closest Item in this branch by name similarity, or None."""
    candidates = list(Item.objects.filter(branch=branch).values_list("id", "name"))
    if not candidates:
        return None

    names = [name for _, name in candidates]
    matches = difflib.get_close_matches(product_name, names, n=1, cutoff=threshold)
    if not matches:
        return None

    return Item.objects.filter(branch=branch, name=matches[0]).first()


def _find_item(branch, product_name, sku=None, fuzzy=False, fuzzy_threshold=0.85):
    """Locate an existing Item using SKU, exact name, or optional fuzzy name."""
    if sku:
        variant = (
            ItemVariant.objects.select_related("item")
            .filter(sku=sku, item__branch=branch)
            .first()
        )
        if variant:
            return variant.item, "sku"

    item = Item.objects.filter(branch=branch, name=product_name).first()
    if item:
        return item, "name"

    if fuzzy:
        item = _fuzzy_find_item(branch, product_name, fuzzy_threshold)
        if item:
            return item, "fuzzy"

    return None, None


def _find_variant(item, variant_name, sku=None):
    """Locate an existing variant by SKU or variant name."""
    if sku:
        variant = ItemVariant.objects.filter(sku=sku).first()
        if variant and variant.item_id == item.id:
            return variant
        if variant and variant.item_id != item.id:
            raise ValueError(f"SKU '{sku}' belongs to a different product.")

    return ItemVariant.objects.filter(item=item, name=variant_name).first()


def _quantity_change_preview(variant, target_qty):
    current = variant.quantity if variant is not None else 0
    if current == target_qty:
        return None
    return {"old": current, "new": target_qty, "delta": target_qty - current}


def _sync_variant_quantity(
    variant,
    target_qty,
    selling_price,
    *,
    business,
    sync_supply,
    batch_number,
    expire_date,
    dry_run=False,
):
    """Set variant stock to target_qty, adjusting supplied batches when possible."""
    current = variant.quantity
    if current == target_qty:
        return None

    delta = target_qty - current
    if dry_run:
        return {"old": current, "new": target_qty, "delta": delta}

    if delta > 0:
        price = selling_price
        if price is None:
            latest = variant.supplied_items.order_by("-created_at").first()
            price = latest.selling_price if latest else None

        if price is not None and sync_supply is not None:
            SuppliedItem.objects.create(
                supply=sync_supply,
                item=variant.item,
                variant=variant,
                quantity=delta,
                initial_quantity=delta,
                selling_price=price,
                purchase_price=None,
                batch_number=batch_number,
                product_number=(variant.sku or f"{variant.item.name} — {variant.name}")[
                    :255
                ],
                business=business,
                expire_date=expire_date,
            )
        else:
            variant.quantity = target_qty
            variant.save(update_fields=["quantity", "updated_at"])
    else:
        remaining = abs(delta)
        for supplied in variant.supplied_items.order_by("-created_at"):
            if remaining <= 0:
                break
            take = min(supplied.quantity, remaining)
            supplied.quantity -= take
            supplied.save(update_fields=["quantity", "updated_at"])
            remaining -= take

        variant.quantity = target_qty
        variant.save(update_fields=["quantity", "updated_at"])

    return {"old": current, "new": target_qty, "delta": delta}


class Command(BaseCommand):
    help = (
        "Sync branch inventory from a CSV/Excel file: update names and quantities "
        "for existing products and create any that are missing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path",
            type=str,
            help="Path to the CSV or Excel file (same columns as bulk export/import).",
        )
        parser.add_argument(
            "--branch",
            dest="branch_id",
            type=str,
            required=True,
            help="UUID of the branch whose inventory should be synced.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to the database.",
        )
        parser.add_argument(
            "--fuzzy-match",
            action="store_true",
            help=(
                "When an exact name match fails, match the closest existing product "
                "name in the branch (useful for minor typo fixes)."
            ),
        )
        parser.add_argument(
            "--fuzzy-threshold",
            type=float,
            default=0.85,
            help="Minimum similarity ratio (0–1) for --fuzzy-match (default: 0.85).",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file_path"])
        branch_id = options["branch_id"]
        dry_run = options["dry_run"]
        fuzzy_match = options["fuzzy_match"]
        fuzzy_threshold = options["fuzzy_threshold"]

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        try:
            branch = Branch.objects.select_related("business").get(id=branch_id)
        except Branch.DoesNotExist as exc:
            raise CommandError(f"Branch not found: {branch_id}") from exc

        business = branch.business
        if business is None:
            raise CommandError(f"Branch {branch_id} has no associated business.")

        rows = _rows_from_path(file_path)
        if not rows:
            raise CommandError("The file contains no data rows.")

        missing_columns = [
            col for col in ("name", "inventory_unit") if col not in (rows[0] or {})
        ]
        if missing_columns:
            raise CommandError(
                f"Missing required columns: {', '.join(missing_columns)}. "
                f"Expected: {', '.join(BULK_IMPORT_COLUMNS)}"
            )

        groups = OrderedDict()
        for row_num, row in enumerate(rows, start=2):
            if not any(str(v).strip() for v in row.values()):
                continue
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            groups.setdefault(name, []).append((row_num, row))

        sync_supply_label = f"sync-{timezone.now():%Y%m%d-%H%M%S}"
        needs_supply = any(
            _parse_int(row.get("quantity"), default=0) > 0
            and _parse_decimal(str(row.get("selling_price", "")).strip()) is not None
            for _, row in ((rn, r) for rs in groups.values() for rn, r in rs)
        )

        summary = {
            "created_items": [],
            "updated_items": [],
            "renamed_items": [],
            "created_variants": [],
            "updated_variants": [],
            "quantity_changes": [],
            "errors": [],
        }

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run — no changes will be saved.\n")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Syncing inventory...\n"))

        with transaction.atomic():
            sync_supply = None
            if needs_supply and not dry_run:
                sync_supply, _ = Supply.objects.get_or_create(
                    branch=branch,
                    label=sync_supply_label,
                    defaults={"business": business},
                )

            for product_name, group_rows in groups.items():
                first_row_num, first_row = group_rows[0]
                inventory_unit = str(first_row.get("inventory_unit", "")).strip()

                if not inventory_unit:
                    summary["errors"].append(
                        {
                            "row": first_row_num,
                            "name": product_name,
                            "errors": ["'inventory_unit' is required."],
                        }
                    )
                    continue

                first_sku = str(first_row.get("sku", "")).strip() or None
                item, match_method = _find_item(
                    branch,
                    product_name,
                    sku=first_sku,
                    fuzzy=fuzzy_match,
                    fuzzy_threshold=fuzzy_threshold,
                )

                raw_groups = str(first_row.get("groups", "")).strip()
                group_names = [g.strip() for g in raw_groups.split(",") if g.strip()]
                resolved_groups = []
                for gname in group_names:
                    if dry_run:
                        resolved_groups.append(gname)
                    else:
                        grp, _ = Group.objects.get_or_create(
                            name=gname, business=business
                        )
                        resolved_groups.append(grp)

                description = str(first_row.get("description", "")).strip() or None

                try:
                    if item is None:
                        if dry_run:
                            summary["created_items"].append(
                                {"row": first_row_num, "name": product_name}
                            )
                            item_created = True
                            item = None
                        else:
                            item = Item.objects.create(
                                name=product_name,
                                branch=branch,
                                description=description,
                                inventory_unit=inventory_unit,
                                business=business,
                                group=resolved_groups[0] if resolved_groups else None,
                            )
                            summary["created_items"].append(
                                {"row": first_row_num, "name": product_name}
                            )
                            item_created = True
                    else:
                        item_created = False
                        old_name = item.name
                        item_updates = []

                        if item.name != product_name:
                            summary["renamed_items"].append(
                                {
                                    "row": first_row_num,
                                    "old_name": old_name,
                                    "new_name": product_name,
                                    "match": match_method,
                                }
                            )
                            if not dry_run:
                                item.name = product_name
                                item_updates.append("name")

                        if description is not None and item.description != description:
                            item_updates.append("description")
                            if not dry_run:
                                item.description = description

                        if item.inventory_unit != inventory_unit:
                            item_updates.append("inventory_unit")
                            if not dry_run:
                                item.inventory_unit = inventory_unit

                        if resolved_groups:
                            item_updates.append("group")
                            if not dry_run:
                                item.group = resolved_groups[0]

                        if item_updates:
                            if not dry_run:
                                item.save(update_fields=item_updates)
                            summary["updated_items"].append(
                                {
                                    "row": first_row_num,
                                    "name": product_name,
                                    "fields": item_updates,
                                }
                            )

                    is_first_variant = item is not None and not item.variants.exists()

                    for row_num, row in group_rows:
                        selling_price_raw = str(row.get("selling_price", "")).strip()
                        selling_price = _parse_decimal(selling_price_raw)
                        if selling_price_raw and selling_price is None:
                            summary["errors"].append(
                                {
                                    "row": row_num,
                                    "name": product_name,
                                    "errors": [
                                        "'selling_price' must be a positive number."
                                    ],
                                }
                            )
                            continue

                        variant_name = (
                            str(row.get("variant_name", "")).strip() or product_name
                        )
                        sku = str(row.get("sku", "")).strip() or None
                        quantity = _parse_int(row.get("quantity"), default=0)
                        batch_number = (
                            str(row.get("batch_number", "")).strip()
                            or sync_supply_label
                        )

                        expired_date_str = str(row.get("expire_date", "")).strip()
                        expire_date = None
                        if expired_date_str:
                            try:
                                expire_date = timezone.datetime.strptime(
                                    expired_date_str, "%Y-%m-%d"
                                ).date()
                            except ValueError:
                                summary["errors"].append(
                                    {
                                        "row": row_num,
                                        "name": product_name,
                                        "errors": [
                                            "'expire_date' must be in YYYY-MM-DD format."
                                        ],
                                    }
                                )
                                continue

                        variant = None
                        if item is not None and not item_created:
                            try:
                                variant = _find_variant(item, variant_name, sku=sku)
                            except ValueError as exc:
                                summary["errors"].append(
                                    {
                                        "row": row_num,
                                        "name": product_name,
                                        "errors": [str(exc)],
                                    }
                                )
                                continue

                        if dry_run:
                            if variant is None:
                                summary["created_variants"].append(
                                    {
                                        "row": row_num,
                                        "product": product_name,
                                        "variant": variant_name,
                                    }
                                )
                            else:
                                variant_updates = []
                                if variant.name != variant_name:
                                    variant_updates.append("name")
                                if variant.sku != sku:
                                    variant_updates.append("sku")
                                if variant_updates:
                                    summary["updated_variants"].append(
                                        {
                                            "row": row_num,
                                            "product": product_name,
                                            "variant": variant_name,
                                            "fields": variant_updates,
                                        }
                                    )

                            qty_change = _quantity_change_preview(variant, quantity)
                            if qty_change:
                                summary["quantity_changes"].append(
                                    {
                                        "row": row_num,
                                        "product": product_name,
                                        "variant": variant_name,
                                        **qty_change,
                                    }
                                )
                            continue

                        if variant is None:
                            variant = ItemVariant.objects.create(
                                item=item,
                                name=variant_name,
                                quantity=0,
                                sku=sku,
                                is_default=is_first_variant,
                            )
                            is_first_variant = False
                            summary["created_variants"].append(
                                {
                                    "row": row_num,
                                    "product": product_name,
                                    "variant": variant_name,
                                }
                            )
                        else:
                            variant_updates = []
                            if variant.name != variant_name:
                                variant.name = variant_name
                                variant_updates.append("name")
                            if variant.sku != sku:
                                variant.sku = sku
                                variant_updates.append("sku")
                            if variant_updates:
                                variant.save(update_fields=variant_updates)
                                summary["updated_variants"].append(
                                    {
                                        "row": row_num,
                                        "product": product_name,
                                        "variant": variant_name,
                                        "fields": variant_updates,
                                    }
                                )

                        if selling_price is not None:
                            latest = variant.supplied_items.order_by(
                                "-created_at"
                            ).first()
                            if latest and latest.selling_price != selling_price:
                                latest.selling_price = selling_price
                                latest.save(update_fields=["selling_price"])

                        qty_change = _sync_variant_quantity(
                            variant,
                            quantity,
                            selling_price,
                            business=business,
                            sync_supply=sync_supply,
                            batch_number=batch_number,
                            expire_date=expire_date,
                            dry_run=False,
                        )
                        if qty_change:
                            summary["quantity_changes"].append(
                                {
                                    "row": row_num,
                                    "product": product_name,
                                    "variant": variant_name,
                                    **qty_change,
                                }
                            )

                except Exception as exc:
                    summary["errors"].append(
                        {
                            "row": first_row_num,
                            "name": product_name,
                            "errors": [str(exc)],
                        }
                    )

            if dry_run:
                transaction.set_rollback(True)

        self._print_report(summary, dry_run=dry_run, supply_label=sync_supply_label)

    def _print_report(self, summary, *, dry_run, supply_label):
        prefix = "Would" if dry_run else ""

        if summary["renamed_items"]:
            self.stdout.write(self.style.HTTP_INFO(f"\n{prefix} rename products:"))
            for entry in summary["renamed_items"]:
                self.stdout.write(
                    f"  row {entry['row']}: "
                    f"'{entry['old_name']}' → '{entry['new_name']}' "
                    f"(matched by {entry['match']})"
                )

        if summary["created_items"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{prefix} create {len(summary['created_items'])} product(s):"
                )
            )
            for entry in summary["created_items"]:
                self.stdout.write(f"  row {entry['row']}: {entry['name']}")

        if summary["updated_items"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{prefix} update {len(summary['updated_items'])} product(s):"
                )
            )
            for entry in summary["updated_items"]:
                self.stdout.write(
                    f"  row {entry['row']}: {entry['name']} ({', '.join(entry['fields'])})"
                )

        if summary["created_variants"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{prefix} create {len(summary['created_variants'])} variant(s):"
                )
            )
            for entry in summary["created_variants"]:
                self.stdout.write(
                    f"  row {entry['row']}: {entry['product']} / {entry['variant']}"
                )

        if summary["updated_variants"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{prefix} update {len(summary['updated_variants'])} variant(s):"
                )
            )
            for entry in summary["updated_variants"]:
                self.stdout.write(
                    f"  row {entry['row']}: {entry['product']} / {entry['variant']} "
                    f"({', '.join(entry['fields'])})"
                )

        if summary["quantity_changes"]:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{prefix} adjust quantity for {len(summary['quantity_changes'])} variant(s):"
                )
            )
            for entry in summary["quantity_changes"]:
                self.stdout.write(
                    f"  row {entry['row']}: {entry['product']} / {entry['variant']} "
                    f"{entry['old']} → {entry['new']}"
                )

        if summary["errors"]:
            self.stdout.write(self.style.ERROR(f"\n{len(summary['errors'])} error(s):"))
            for entry in summary["errors"]:
                self.stdout.write(
                    f"  row {entry['row']}: {entry['name']} — {', '.join(entry['errors'])}"
                )

        if not dry_run and summary["quantity_changes"] and supply_label:
            self.stdout.write(
                self.style.NOTICE(
                    f"\nStock adjustments recorded under supply: {supply_label}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. "
                f"Created {len(summary['created_items'])} product(s), "
                f"renamed {len(summary['renamed_items'])}, "
                f"quantity changes {len(summary['quantity_changes'])}, "
                f"errors {len(summary['errors'])}."
            )
        )
