from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Order, OrderHistory, OrderItem, OrderReturn, OrderReturnItem

User = get_user_model()


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        "variant",
        "supplied_item",
        "quantity",
        "price",
        "batch_number_display",
        "expire_date_display",
    )
    readonly_fields = (
        "batch_number_display",
        "expire_date_display",
    )
    raw_id_fields = ("variant", "supplied_item")
    show_change_link = True

    def batch_number_display(self, obj):
        if obj.pk and obj.supplied_item_id:
            return obj.supplied_item.batch_number or "—"
        return "—"

    batch_number_display.short_description = "Batch #"

    def expire_date_display(self, obj):
        if obj.pk and obj.supplied_item_id:
            return obj.supplied_item.expire_date or "—"
        return "—"

    expire_date_display.short_description = "Expires"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("variant__item", "supplied_item")
        )


class OrderHistoryInline(admin.TabularInline):
    model = OrderHistory
    extra = 0
    fields = (
        "field_name",
        "old_value",
        "new_value",
        "changed_by",
        "change_reason",
        "created_at",
    )
    readonly_fields = (
        "field_name",
        "old_value",
        "new_value",
        "changed_by",
        "change_reason",
        "created_at",
    )
    can_delete = False
    ordering = ("-created_at",)
    max_num = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("changed_by")


class OrderReturnItemInline(admin.TabularInline):
    model = OrderReturnItem
    extra = 0
    fields = (
        "item_name_display",
        "variant_name_display",
        "batch_number_display",
        "quantity_returned",
        "refund_amount",
        "is_restocked",
    )
    readonly_fields = (
        "item_name_display",
        "variant_name_display",
        "batch_number_display",
        "quantity_returned",
        "refund_amount",
        "is_restocked",
    )
    can_delete = False

    def item_name_display(self, obj):
        try:
            return obj.order_item.variant.item.name
        except Exception:
            return "—"

    item_name_display.short_description = "Item"

    def variant_name_display(self, obj):
        try:
            return obj.order_item.variant.name
        except Exception:
            return "—"

    variant_name_display.short_description = "Variant"

    def batch_number_display(self, obj):
        try:
            si = obj.order_item.supplied_item
            return si.batch_number if si else "—"
        except Exception:
            return "—"

    batch_number_display.short_description = "Batch #"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "order_item__variant__item",
                "order_item__supplied_item",
            )
        )


# ---------------------------------------------------------------------------
# Order admin
# ---------------------------------------------------------------------------

_STATUS_COLORS = {
    "COMPLETED": "#28a745",
    "PARTIALLY_PAID": "#17a2b8",
    "PAID": "#17a2b8",
    "PROCESSING": "#ffc107",
    "PENDING": "#fd7e14",
    "CANCELLED": "#dc3545",
    "REFUNDED": "#dc3545",
    "RETURNED": "#6f42c1",
    "ON_HOLD": "#6c757d",
}


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "short_id",
        "customer_info",
        "employee_info",
        "colored_status",
        "total_payable",
        "payment_method",
        "item_count",
        "branch",
        "business",
        "created_at",
    ]
    list_filter = ["status", "branch", "business", "created_at"]
    search_fields = [
        "id",
        "customer__full_name",
        "customer__phone_number",
        "employee__user__first_name",
        "employee__user__last_name",
        "transaction_id",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["customer", "employee", "payment_method"]
    inlines = [OrderItemInline, OrderHistoryInline]
    actions = ["mark_as_completed", "mark_as_cancelled"]

    fieldsets = (
        (
            None,
            {"fields": ("id", "customer", "employee", "status")},
        ),
        (
            _("Business"),
            {"fields": ("business", "branch")},
        ),
        (
            _("Financial"),
            {
                "fields": (
                    "total_payable",
                    "payment_method",
                    "transaction_id",
                    "receipt",
                )
            },
        ),
        (
            _("Extra"),
            {"fields": ("additional_info",), "classes": ("collapse",)},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "customer",
                "employee__user",
                "payment_method",
                "business",
                "branch",
            )
            .prefetch_related("items")
        )

    def short_id(self, obj):
        return str(obj.id)[:8] + "…"

    short_id.short_description = "Order ID"
    short_id.admin_order_field = "id"

    def customer_info(self, obj):
        if not obj.customer_id:
            return "—"
        return obj.customer.full_name

    customer_info.short_description = "Customer"

    def employee_info(self, obj):
        if not obj.employee_id:
            return "—"
        emp = obj.employee
        return emp.full_name if emp else "—"

    employee_info.short_description = "Employee"

    def item_count(self, obj):
        return obj.items.all().count()

    item_count.short_description = "# Items"

    def colored_status(self, obj):
        color = _STATUS_COLORS.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            color,
            obj.get_status_display(),
        )

    colored_status.short_description = "Status"

    @admin.action(description="Mark selected orders as completed")
    def mark_as_completed(self, request, queryset):
        queryset.update(status=Order.StatusChoices.COMPLETED)

    @admin.action(description="Mark selected orders as cancelled")
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status=Order.StatusChoices.CANCELLED)


# ---------------------------------------------------------------------------
# OrderItem standalone admin
# ---------------------------------------------------------------------------


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order_short_id",
        "item_name",
        "variant_name",
        "supplied_batch",
        "supplied_selling_price",
        "quantity",
        "price",
        "order_status",
        "created_at",
    ]
    list_filter = ["order__status", "created_at"]
    search_fields = [
        "order__id",
        "variant__name",
        "variant__item__name",
        "supplied_item__batch_number",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "batch_number_display",
        "product_number_display",
        "selling_price_display",
        "purchase_price_display",
        "expire_date_display",
        "man_date_display",
    ]
    raw_id_fields = ["order", "variant", "supplied_item"]

    fieldsets = (
        (
            None,
            {"fields": ("id", "order", "variant", "quantity", "price")},
        ),
        (
            _("Supplied Item"),
            {
                "fields": (
                    "supplied_item",
                    "batch_number_display",
                    "product_number_display",
                    "selling_price_display",
                    "purchase_price_display",
                    "expire_date_display",
                    "man_date_display",
                ),
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "variant__item__business",
                "order",
                "supplied_item",
            )
        )

    def order_short_id(self, obj):
        return str(obj.order_id)[:8] + "…"

    order_short_id.short_description = "Order"

    def item_name(self, obj):
        try:
            return obj.variant.item.name
        except Exception:
            return "—"

    item_name.short_description = "Item"

    def variant_name(self, obj):
        return obj.variant.name if obj.variant_id else "—"

    variant_name.short_description = "Variant"

    def supplied_batch(self, obj):
        if obj.supplied_item_id:
            return obj.supplied_item.batch_number or "—"
        return "—"

    supplied_batch.short_description = "Batch #"

    def supplied_selling_price(self, obj):
        if obj.supplied_item_id:
            return obj.supplied_item.selling_price
        return "—"

    supplied_selling_price.short_description = "Sell Price"

    def order_status(self, obj):
        return obj.order.get_status_display()

    order_status.short_description = "Order Status"

    # Detail-page readonly helpers
    def batch_number_display(self, obj):
        return obj.supplied_item.batch_number if obj.supplied_item_id else "—"

    batch_number_display.short_description = "Batch #"

    def product_number_display(self, obj):
        return obj.supplied_item.product_number if obj.supplied_item_id else "—"

    product_number_display.short_description = "Product #"

    def selling_price_display(self, obj):
        return obj.supplied_item.selling_price if obj.supplied_item_id else "—"

    selling_price_display.short_description = "Selling Price"

    def purchase_price_display(self, obj):
        return obj.supplied_item.purchase_price if obj.supplied_item_id else "—"

    purchase_price_display.short_description = "Purchase Price"

    def expire_date_display(self, obj):
        return obj.supplied_item.expire_date if obj.supplied_item_id else "—"

    expire_date_display.short_description = "Expiry Date"

    def man_date_display(self, obj):
        return obj.supplied_item.man_date if obj.supplied_item_id else "—"

    man_date_display.short_description = "Manufacture Date"


# ---------------------------------------------------------------------------
# OrderReturn admin
# ---------------------------------------------------------------------------


@admin.register(OrderReturn)
class OrderReturnAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order",
        "status",
        "total_refund_amount",
        "refund_method",
        "processed_by",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["order__id", "processed_by__user__email"]
    readonly_fields = ["id", "created_at", "updated_at", "total_refund_amount"]
    raw_id_fields = ["order", "processed_by", "refund_method"]
    inlines = [OrderReturnItemInline]

    fieldsets = (
        (None, {"fields": ("id", "order", "status", "reason")}),
        (_("Financial"), {"fields": ("total_refund_amount", "refund_method")}),
        (_("Processed by"), {"fields": ("processed_by",)}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("order", "refund_method", "processed_by__user")
        )
