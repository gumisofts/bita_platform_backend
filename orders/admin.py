from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import *

User = get_user_model()


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("variant", "quantity")
    raw_id_fields = ("variant",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "customer_info",
        "employee_info",
        "status",
        "total_payable",
        "item_count",
        "created_at",
    ]
    list_filter = ["status", "created_at", "branch", "business"]
    search_fields = ["customer", "employee"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [OrderItemInline]

    fieldsets = (
        (None, {"fields": ("id", "customer", "employee", "status")}),
        (_("Financial"), {"fields": ("total_payable",)}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def customer_info(self, obj):
        try:
            if obj.customer:
                return f"{obj.customer.email} ({obj.customer.full_name})"
            else:
                return "N/A"
        except User.DoesNotExist:
            return f"Customer ID: {obj.customer.id}"

    customer_info.short_description = "Customer"

    def employee_info(self, obj):
        try:
            if obj.employee and obj.employee.user:
                return f"{obj.employee.user.email} ({obj.employee.full_name})"
            else:
                return "N/A"
        except User.DoesNotExist:
            return f"Employee ID: {obj.employee.id}"

    employee_info.short_description = "Employee"

    def item_count(self, obj):
        count = obj.items.count()
        return f"{count} items"

    item_count.short_description = "Items"

    def get_status_color(self, status):
        colors = {
            "PROCESSING": "#ffc107",  # Yellow
            "COMPLETED": "#28a745",  # Green
            "CANCELLED": "#dc3545",  # Red
            "PARTIALLY_PAID": "#17a2b8",  # Blue
        }
        return colors.get(status, "#6c757d")  # Default gray

    def colored_status(self, obj):
        color = self.get_status_color(obj.status)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    colored_status.short_description = "Status"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order_id",
        "variant_name",
        "item_business",
        "quantity",
        "order_status",
        "created_at",
    ]
    list_filter = ["order__status", "created_at"]
    search_fields = ["order__id", "variant__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["order", "variant"]

    fieldsets = (
        (None, {"fields": ("id", "order", "variant", "quantity")}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def order_id(self, obj):
        return str(obj.order.id)[:8] + "..."

    order_id.short_description = "Order ID"

    def variant_name(self, obj):
        return obj.variant.name if obj.variant else "-"

    variant_name.short_description = "Item"

    def item_business(self, obj):
        if obj.variant and obj.variant.business:
            return obj.variant.business.name
        return "-"

    item_business.short_description = "Business"

    def order_status(self, obj):
        return obj.order.get_status_display()

    order_status.short_description = "Order Status"


# Custom admin actions
@admin.action(description="Mark selected orders as completed")
def mark_as_completed(modeladmin, request, queryset):
    queryset.update(status="COMPLETED")


@admin.action(description="Mark selected orders as cancelled")
def mark_as_cancelled(modeladmin, request, queryset):
    queryset.update(status="CANCELLED")


# Add actions to OrderAdmin
OrderAdmin.actions = [mark_as_completed, mark_as_cancelled]
