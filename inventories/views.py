import csv
import io

import openpyxl
from django.contrib.postgres.search import TrigramSimilarity
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.utils import timezone
from guardian.shortcuts import assign_perm, get_objects_for_user, get_perms, remove_perm
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from business.models import AdditionalBusinessPermissionNames, Business
from business.permissions import (
    BranchLevelPermission,
    BusinessLevelPermission,
    GuardianObjectPermissions,
)

from .filters import GroupFilter, ItemFilter, ItemVariantFilter, SupplierFilter
from .models import *
from .serializers import *


class ItemViewset(ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    filterset_class = ItemFilter

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ItemReadSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM.value[0] + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM.value[0] + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()
        return queryset

    # ------------------------------------------------------------------
    # Import / export shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_int(value, default=0):
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_decimal(value):
        try:
            v = float(str(value).strip())
            return v if v > 0 else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _rows_from_file(uploaded_file):
        """Parse CSV or Excel upload into a list of dicts keyed by column name."""
        fname = uploaded_file.name.lower()
        if fname.endswith(".csv"):
            text = uploaded_file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            return [{k.strip(): (v or "") for k, v in row.items()} for row in reader]
        wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
        ws = wb.active
        raw = list(ws.iter_rows(values_only=True))
        if not raw:
            return []
        headers = [str(h).strip() if h is not None else "" for h in raw[0]]
        return [
            {headers[i]: ("" if v is None else str(v)) for i, v in enumerate(row)}
            for row in raw[1:]
        ]

    @staticmethod
    def _build_xlsx_response(wb, filename):
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    @staticmethod
    def _styled_wb_sheet(wb, title):
        """Return (worksheet, header_fill, header_font, thin_border) helpers."""
        ws = wb.active if wb.sheetnames == ["Sheet"] else wb.create_sheet(title)
        ws.title = title
        fill = openpyxl.styles.PatternFill("solid", fgColor="1F4E79")
        font = openpyxl.styles.Font(bold=True, color="FFFFFF", size=11)
        border = openpyxl.styles.Border(
            left=openpyxl.styles.Side(style="thin"),
            right=openpyxl.styles.Side(style="thin"),
            top=openpyxl.styles.Side(style="thin"),
            bottom=openpyxl.styles.Side(style="thin"),
        )
        return ws, fill, font, border

    @staticmethod
    def _write_xlsx_headers(ws, columns, fill, font, border):
        center = openpyxl.styles.Alignment(horizontal="center", vertical="center")
        for col_idx, col_name in enumerate(columns, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill = fill
            cell.font = font
            cell.alignment = center
            cell.border = border
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 24
        ws.row_dimensions[1].height = 25

    # ------------------------------------------------------------------
    # Template download
    # ------------------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="bulk-import-template",
        permission_classes=[IsAuthenticated],
    )
    def bulk_import_template(self, request):
        """Download a styled Excel template for bulk product import."""
        wb = openpyxl.Workbook()
        ws, fill, font, border = self._styled_wb_sheet(wb, "Products")
        self._write_xlsx_headers(ws, BULK_IMPORT_COLUMNS, fill, font, border)

        # Sample rows — two variants for the same product show multi-variant usage
        sample_rows = [
            # name               description           unit    variant_name  price   sku        qty
            [
                "Paracetamol",
                "Pain relief tablet",
                "piece",
                "100mg",
                25.00,
                "SKU-P100",
                100,
            ],
            ["Paracetamol", "", "piece", "500mg", 45.00, "SKU-P500", 50],
            ["Vitamin C", "Immune support", "piece", "", 35.00, "", 200],
            [
                "Amoxicillin 250mg",
                "Antibiotic capsule",
                "piece",
                "",
                60.00,
                "SKU-A250",
                80,
            ],
        ]
        row_font = openpyxl.styles.Font(size=10)
        for row_idx, row in enumerate(sample_rows, start=2):
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = row_font
                cell.border = border

        # Instructions sheet
        ws2 = wb.create_sheet("Instructions")
        ws2.column_dimensions["A"].width = 20
        ws2.column_dimensions["B"].width = 70
        title_cell = ws2["A1"]
        title_cell.value = "Bulk Product Import — Column Reference"
        title_cell.font = openpyxl.styles.Font(bold=True, size=13, color="1F4E79")
        ws2.merge_cells("A1:B1")
        ws2.row_dimensions[1].height = 22

        ws2.cell(row=2, column=1, value="Column").font = openpyxl.styles.Font(bold=True)
        ws2.cell(row=2, column=2, value="Description").font = openpyxl.styles.Font(
            bold=True
        )
        for row_idx, col_name in enumerate(BULK_IMPORT_COLUMNS, start=3):
            ws2.cell(row=row_idx, column=1, value=col_name).font = openpyxl.styles.Font(
                bold=True
            )
            ws2.cell(
                row=row_idx, column=2, value=BULK_IMPORT_COLUMN_NOTES.get(col_name, "")
            )

        note_row = 3 + len(BULK_IMPORT_COLUMNS) + 1
        ws2.cell(row=note_row, column=1, value="Multi-variant tip:").font = (
            openpyxl.styles.Font(bold=True, color="C00000")
        )
        ws2.cell(
            row=note_row,
            column=2,
            value="To add multiple variants to one product, repeat the product name on consecutive rows with different variant_name and selling_price values.",
        )

        return self._build_xlsx_response(wb, "bulk_product_import_template.xlsx")

    # ------------------------------------------------------------------
    # Bulk import
    # ------------------------------------------------------------------

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-import",
        permission_classes=[
            IsAuthenticated,
            GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
        ],
    )
    def bulk_import(self, request):
        """
        Upload a CSV or Excel file to bulk-create products.

        Format rules:
        - One row per variant.
        - Rows sharing the same `name` belong to the same product — the product is
          created from the first row; subsequent rows add more variants.
        - `variant_name` defaults to the product name when left blank (single-variant products).
        - Existing products/variants are upserted (matched by name+branch for items,
          SKU for variants if provided, else by variant name+item).

        Required columns : name, inventory_unit, selling_price
        Optional columns : description, variant_name, sku, quantity
        """
        serializer = BulkItemImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        try:
            rows = self._rows_from_file(uploaded_file)
        except Exception as exc:
            return Response(
                {"detail": f"Could not parse file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not rows:
            return Response(
                {"detail": "The uploaded file contains no data rows."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        business = request.business
        branch = request.branch

        # ------------------------------------------------------------------
        # Group rows by product name preserving order
        # ------------------------------------------------------------------
        from collections import OrderedDict

        groups = OrderedDict()  # name -> list of (row_num, row_dict)
        for row_num, row in enumerate(rows, start=2):
            if not any(str(v).strip() for v in row.values()):
                continue  # skip blank rows
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            groups.setdefault(name, []).append((row_num, row))

        created_items = []
        created_variants = []
        errors = []

        for product_name, group_rows in groups.items():
            first_row_num, first_row = group_rows[0]
            inventory_unit = str(first_row.get("inventory_unit", "")).strip()

            if not inventory_unit:
                errors.append(
                    {
                        "row": first_row_num,
                        "name": product_name,
                        "errors": ["'inventory_unit' is required."],
                    }
                )
                continue

            # Upsert Item by name + branch
            try:
                with transaction.atomic():
                    item, item_created = Item.objects.get_or_create(
                        name=product_name,
                        branch=branch,
                        defaults={
                            "description": str(first_row.get("description", "")).strip()
                            or None,
                            "inventory_unit": inventory_unit,
                            "business": business,
                        },
                    )
                    if item_created:
                        created_items.append(
                            {"row": first_row_num, "name": product_name}
                        )

                    is_first_variant = not item.variants.exists()

                    for row_num, row in group_rows:
                        selling_price = self._parse_decimal(
                            row.get("selling_price", "")
                        )
                        if selling_price is None:
                            errors.append(
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
                        quantity = self._parse_int(row.get("quantity"), default=0)

                        # Upsert variant: match by SKU (if given) else by name+item
                        variant = None
                        if sku:
                            variant = ItemVariant.objects.filter(sku=sku).first()
                            if variant and variant.item != item:
                                errors.append(
                                    {
                                        "row": row_num,
                                        "name": product_name,
                                        "errors": [
                                            f"SKU '{sku}' belongs to a different product."
                                        ],
                                    }
                                )
                                continue
                        if variant is None:
                            variant = ItemVariant.objects.filter(
                                item=item, name=variant_name
                            ).first()

                        if variant:
                            variant.selling_price = selling_price
                            variant.quantity = quantity
                            variant.sku = sku
                            variant.save()
                        else:
                            ItemVariant.objects.create(
                                item=item,
                                name=variant_name,
                                selling_price=selling_price,
                                quantity=quantity,
                                sku=sku,
                                is_default=is_first_variant,
                            )
                            is_first_variant = False

                        created_variants.append(
                            {
                                "row": row_num,
                                "product": product_name,
                                "variant": variant_name,
                            }
                        )

            except Exception as exc:
                errors.append(
                    {"row": first_row_num, "name": product_name, "errors": [str(exc)]}
                )

        return Response(
            {
                "products_created": len(created_items),
                "variants_processed": len(created_variants),
                "error_count": len(errors),
                "products": created_items,
                "variants": created_variants,
                "errors": errors,
            },
            status=status.HTTP_207_MULTI_STATUS if errors else status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="export",
        permission_classes=[
            IsAuthenticated,
            GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
        ],
    )
    def export(self, request):
        """
        Export all products for the current branch as CSV or Excel.

        One row per variant. Importing the exported file reproduces the same data.

        Query params:
          format : 'csv' | 'xlsx'  (default: xlsx)
        """
        fmt = request.query_params.get("format", "xlsx").lower()

        items = self.get_queryset().prefetch_related("variants").order_by("name")

        # Build flat rows — one per variant
        data_rows = []
        for item in items:
            variants = list(item.variants.order_by("name"))
            if not variants:
                # Emit one placeholder row so the product is not silently lost
                data_rows.append(
                    [
                        item.name,
                        item.description or "",
                        item.inventory_unit,
                        "",  # variant_name (will default to product name on re-import)
                        "",  # selling_price — user must fill in
                        "",  # sku
                        item.quantity,
                    ]
                )
            else:
                for variant in variants:
                    data_rows.append(
                        [
                            item.name,
                            item.description or "",
                            item.inventory_unit,
                            "" if variant.name == item.name else variant.name,
                            str(variant.selling_price) if variant.selling_price else "",
                            variant.sku or "",
                            variant.quantity,
                        ]
                    )

        if fmt == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = (
                'attachment; filename="products_export.csv"'
            )
            response.write("\ufeff")  # UTF-8 BOM for Excel compatibility
            writer = csv.writer(response)
            writer.writerow(BULK_IMPORT_COLUMNS)
            writer.writerows(data_rows)
            return response

        # Default: xlsx
        wb = openpyxl.Workbook()
        ws, fill, font, border = self._styled_wb_sheet(wb, "Products")
        self._write_xlsx_headers(ws, BULK_IMPORT_COLUMNS, fill, font, border)

        row_font = openpyxl.styles.Font(size=10)

        # Colour alternate product blocks to make grouping visible
        palette = ["FFFFFF", "EBF3FB"]
        current_product = None
        colour_idx = 0
        for row_idx, row in enumerate(data_rows, start=2):
            if row[0] != current_product:
                current_product = row[0]
                colour_idx = (colour_idx + 1) % 2
            row_fill = openpyxl.styles.PatternFill("solid", fgColor=palette[colour_idx])
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = row_font
                cell.border = border
                cell.fill = row_fill

        return self._build_xlsx_response(wb, "products_export.xlsx")


class SupplyViewset(
    ListModelMixin, CreateModelMixin, RetrieveModelMixin, GenericViewSet
):
    serializer_class = SupplySerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    queryset = Supply.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_SUPPLY.value[0] + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_SUPPLY.value[0] + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()
        return queryset.order_by("-updated_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SupplyDetailsSerializer
        return self.serializer_class


class SupplierViewset(ListModelMixin, CreateModelMixin, GenericViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    queryset = Supplier.objects.all()
    filterset_class = SupplierFilter

    def get_queryset(self):
        queryset = self.queryset
        return queryset.filter(business=self.request.business)


class SupplyItemViewset(CreateModelMixin, GenericViewSet):
    serializer_class = SuppliedItemSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    queryset = SuppliedItem.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        supply_id = self.request.query_params.get("supply_id")
        if supply_id:
            queryset = queryset.filter(supply=supply_id)
        return queryset


class PricingViewset(
    CreateModelMixin, DestroyModelMixin, UpdateModelMixin, GenericViewSet
):
    queryset = (
        ItemVariant.objects.all()
    )  # Leave here to check for variant permission checks on business and branch level
    serializer_class = PricingSerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission,
    ]

    def get_queryset(self):
        return Pricing.objects.all()


class GroupViewset(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    filterset_class = GroupFilter

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_GROUP.value[0] + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_GROUP.value[0] + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()
        return queryset


class ItemVariantViewset(ModelViewSet):
    queryset = ItemVariant.objects.all()
    serializer_class = ItemVariantSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    filterset_class = ItemVariantFilter

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ItemVariantReadSerializer
        if self.action == "list":
            return ItemVariantReadSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = self.queryset
        item = self.request.query_params.get("item")
        if item:
            queryset = queryset.filter(item=item)

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM_VARIANT.value[0]
            + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(item__business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM_VARIANT.value[0]
            + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(item__branch=self.request.branch)
        else:
            queryset = queryset.none()

        return queryset.order_by(Lower("name"), "id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            ItemVariantReadSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            ItemVariantReadSerializer(serializer.instance).data,
            status=status.HTTP_200_OK,
        )


class PropertyViewset(
    CreateModelMixin, DestroyModelMixin, UpdateModelMixin, GenericViewSet
):
    queryset = (
        ItemVariant.objects.all()
    )  # Leave here to check for variant permission checks on business and branch level
    serializer_class = PropertySerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission,
    ]

    def get_queryset(self):
        return Property.objects.all()


class InventoryMovementViewSet(ModelViewSet):
    """ViewSet for managing inventory movements between branches"""

    queryset = InventoryMovement.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return InventoryMovementCreateSerializer
        return InventoryMovementSerializer

    def get_queryset(self):
        queryset = self.queryset.select_related(
            "from_branch", "to_branch", "business", "requested_by"
        ).prefetch_related("movement_items__supplied_item__item")

        user = self.request.user
        business_id = self.request.query_params.get("business_id")
        branch_id = self.request.query_params.get("branch_id")
        status_filter = self.request.query_params.get("status")

        if business_id:
            queryset = queryset.filter(business_id=business_id)

        if branch_id:
            # Show movements where user's branch is either source or destination
            queryset = queryset.filter(
                Q(from_branch_id=branch_id) | Q(to_branch_id=branch_id)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a pending inventory movement"""
        movement = self.get_object()

        if movement.status != "pending":
            return Response(
                {"error": "Only pending movements can be approved"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            movement.status = "approved"
            movement.approved_by = request.user
            movement.approved_at = timezone.now()
            movement.save()

        serializer = self.get_serializer(movement)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        """Mark movement as shipped and reduce inventory from source"""
        movement = self.get_object()

        if movement.status != "approved":
            return Response(
                {"error": "Only approved movements can be shipped"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shipped_items = request.data.get("items", [])

        with transaction.atomic():
            for item_data in shipped_items:
                movement_item = movement.movement_items.get(
                    id=item_data["movement_item_id"]
                )
                quantity_shipped = item_data["quantity_shipped"]

                if quantity_shipped > movement_item.quantity_requested:
                    return Response(
                        {
                            "error": f"Shipped quantity cannot exceed requested quantity for {movement_item.supplied_item.item.name}"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Update movement item
                movement_item.quantity_shipped = quantity_shipped
                movement_item.save()

                # Reduce inventory from source
                movement_item.supplied_item.quantity -= quantity_shipped
                movement_item.supplied_item.save()

            movement.status = "shipped"
            movement.shipped_by = request.user
            movement.shipped_at = timezone.now()
            movement.save()

        serializer = self.get_serializer(movement)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        """Mark movement as received and add inventory to destination"""
        movement = self.get_object()

        if movement.status != "shipped":
            return Response(
                {"error": "Only shipped movements can be received"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        received_items = request.data.get("items", [])

        with transaction.atomic():
            for item_data in received_items:
                movement_item = movement.movement_items.get(
                    id=item_data["movement_item_id"]
                )
                quantity_received = item_data["quantity_received"]

                if quantity_received > movement_item.quantity_shipped:
                    return Response(
                        {
                            "error": f"Received quantity cannot exceed shipped quantity for {movement_item.supplied_item.item.name}"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Update movement item
                movement_item.quantity_received = quantity_received
                movement_item.save()

                # Add inventory to destination
                # First, try to find existing supply in destination branch
                source_supply = movement_item.supplied_item.supply
                source_label = source_supply.label
                if not source_label:
                    # Group by source supply so all items go to same destination supply
                    source_label = f"supply-{source_supply.id}"
                destination_supply, created = Supply.objects.get_or_create(
                    branch=movement.to_branch,
                    label=source_label,
                )

                # Check if same item already exists in destination supply
                existing_supplied_item = SuppliedItem.objects.filter(
                    supply=destination_supply,
                    item=movement_item.supplied_item.item,
                    batch_number=movement_item.supplied_item.batch_number,
                    product_number=movement_item.supplied_item.product_number,
                ).first()

                if existing_supplied_item:
                    # Add to existing stock
                    existing_supplied_item.quantity += quantity_received
                    existing_supplied_item.save()
                else:
                    # Create new supplied item in destination
                    SuppliedItem.objects.create(
                        supply=destination_supply,
                        item=movement_item.supplied_item.item,
                        quantity=quantity_received,
                        selling_price=movement_item.supplied_item.selling_price,
                        purchase_price=movement_item.supplied_item.purchase_price,
                        batch_number=movement_item.supplied_item.batch_number,
                        product_number=f"{movement_item.supplied_item.product_number}-T{movement.id}",  # Avoid duplicate product numbers
                        expire_date=movement_item.supplied_item.expire_date,
                        man_date=movement_item.supplied_item.man_date,
                        business=movement.business,
                        variant=movement_item.variant,
                    )

            movement.status = "received"
            movement.received_by = request.user
            movement.received_at = timezone.now()
            movement.save()

        serializer = self.get_serializer(movement)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a movement (only if pending or approved)"""
        movement = self.get_object()

        if movement.status not in ["pending", "approved"]:
            return Response(
                {"error": "Only pending or approved movements can be cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        movement.status = "cancelled"
        movement.save()

        serializer = self.get_serializer(movement)
        return Response(serializer.data)


class InventoryMovementItemViewSet(ModelViewSet):
    """ViewSet for individual movement items"""

    queryset = InventoryMovementItem.objects.all()
    serializer_class = InventoryMovementItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.select_related("movement", "supplied_item__item")

        movement_id = self.request.query_params.get("movement_id")
        if movement_id:
            queryset = queryset.filter(movement_id=movement_id)

        return queryset
