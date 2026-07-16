from datetime import timedelta

from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from finances.models import *


class BusinessPaymentMethodInline(admin.TabularInline):
    model = BusinessPaymentMethod
    extra = 0
    fields = (
        "payment",
        "label",
        "branch",
        "identifier",
        "receiver_name",
    )
    raw_id_fields = ("payment", "branch")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "short_name",
        "image_preview",
        "business_count",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = ["name", "short_name"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("id", "name", "short_name")}),
        (_("Media"), {"fields": ("image",)}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />',
                obj.image.url,
            )
        return "-"

    image_preview.short_description = "Image"

    def business_count(self, obj):
        count = obj.businesspaymentmethod_set.count()
        return f"{count} businesses"

    business_count.short_description = "Used by"


@admin.register(BusinessPaymentMethod)
class BusinessPaymentMethodAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "business_name",
        "payment_name",
        "display_name",
        "receiver_name",
        "identifier",
        "branch",
        "transactions_link",
        "created_at",
    ]
    list_filter = [
        ("business", admin.RelatedOnlyFieldListFilter),
        "payment",
        "created_at",
    ]
    search_fields = ["business__name", "payment__name", "label", "identifier"]
    readonly_fields = ["id", "created_at", "updated_at"]
    autocomplete_fields = ["business", "branch", "payment"]

    fieldsets = (
        (None, {"fields": ("id", "business", "payment", "branch")}),
        (_("Configuration"), {"fields": ("label", "identifier", "receiver_name")}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("business", "payment", "branch")
        )

    def business_name(self, obj):
        return obj.business.name if obj.business else "-"

    business_name.short_description = "Business"

    def payment_name(self, obj):
        return obj.payment.name if obj.payment else "-"

    payment_name.short_description = "Payment Method"

    def transactions_link(self, obj):
        url = reverse("admin:finances_transaction_changelist")
        return format_html(
            '<a href="{}?payment_method__id__exact={}">View transactions</a>',
            url,
            obj.id,
        )

    transactions_link.short_description = "Transactions"


# ---------------------------------------------------------------------------
# Transaction list filters — tuned for debugging a single business's data.
# ---------------------------------------------------------------------------


class AmountSignFilter(admin.SimpleListFilter):
    """Surfaces sign anomalies (e.g. a SALE stored negative, a REFUND stored
    positive) that are otherwise easy to miss while scrolling a long list."""

    title = "amount sign"
    parameter_name = "amount_sign"

    def lookups(self, request, model_admin):
        return (
            ("positive", "Positive (> 0)"),
            ("negative", "Negative (< 0)"),
            ("zero", "Zero"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "positive":
            return queryset.filter(total_paid_amount__gt=0)
        if value == "negative":
            return queryset.filter(total_paid_amount__lt=0)
        if value == "zero":
            return queryset.filter(total_paid_amount=0)
        return queryset


class HasOrderFilter(admin.SimpleListFilter):
    """Isolates manual/system entries with no linked order, a common source
    of "why doesn't this add up" reports."""

    title = "linked order"
    parameter_name = "has_order"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Has order"),
            ("no", "No order (manual/system entry)"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(order__isnull=False)
        if value == "no":
            return queryset.filter(order__isnull=True)
        return queryset


class QuickDateFilter(admin.SimpleListFilter):
    """Common relative date ranges, faster than clicking through the date
    hierarchy for the ranges support usually cares about."""

    title = "quick date range"
    parameter_name = "quick_date"

    def lookups(self, request, model_admin):
        return (
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("last_7_days", "Last 7 days"),
            ("this_month", "This month"),
            ("last_month", "Last month"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        now = timezone.localtime()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if value == "today":
            return queryset.filter(created_at__gte=today_start)
        if value == "yesterday":
            yesterday_start = today_start - timedelta(days=1)
            return queryset.filter(
                created_at__gte=yesterday_start, created_at__lt=today_start
            )
        if value == "last_7_days":
            return queryset.filter(created_at__gte=today_start - timedelta(days=7))
        if value == "this_month":
            month_start = today_start.replace(day=1)
            return queryset.filter(created_at__gte=month_start)
        if value == "last_month":
            this_month_start = today_start.replace(day=1)
            last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
            return queryset.filter(
                created_at__gte=last_month_start, created_at__lt=this_month_start
            )
        return queryset


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    date_hierarchy = "created_at"
    list_display = [
        "short_id",
        "type_colored",
        "business_name",
        "branch_name",
        "amount_display",
        "payment_method_name",
        "category",
        "order_info",
        "created_by_email",
        "created_at",
    ]
    list_filter = [
        "type",
        AmountSignFilter,
        HasOrderFilter,
        QuickDateFilter,
        ("business", admin.RelatedOnlyFieldListFilter),
        ("branch", admin.RelatedOnlyFieldListFilter),
        ("payment_method", admin.RelatedOnlyFieldListFilter),
        "category",
        "created_at",
    ]
    # "id" and "order__id" let support paste a raw UUID straight from a bug
    # report; the rest cover the usual "which business/branch/method" hunt.
    search_fields = [
        "id",
        "order__id",
        "business__name",
        "branch__name",
        "category",
        "payment_method__label",
        "payment_method__identifier",
        "created_by__email",
        "created_by__first_name",
        "created_by__last_name",
    ]
    autocomplete_fields = [
        "order",
        "business",
        "branch",
        "payment_method",
        "created_by",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]
    list_per_page = 50

    fieldsets = (
        (None, {"fields": ("id", "type", "order", "business", "branch")}),
        (
            _("Financial Details"),
            {"fields": ("total_paid_amount", "payment_method", "category")},
        ),
        (_("Audit"), {"fields": ("created_by",)}),
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
                "order", "business", "branch", "payment_method", "created_by"
            )
        )

    def short_id(self, obj):
        return str(obj.id)[:8] + "..."

    short_id.short_description = "ID"
    short_id.admin_order_field = "id"

    def type_colored(self, obj):
        colors = {
            "SALE": "#28a745",  # Green
            "EXPENSE": "#dc3545",  # Red
            "DEBT": "#ffc107",  # Yellow
            "REFUND": "#17a2b8",  # Blue
        }
        color = colors.get(obj.type, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_type_display(),
        )

    type_colored.short_description = "Type"
    type_colored.admin_order_field = "type"

    def business_name(self, obj):
        if not obj.business_id:
            return "-"
        url = reverse("admin:business_business_change", args=[obj.business_id])
        return format_html('<a href="{}">{}</a>', url, obj.business.name)

    business_name.short_description = "Business"
    business_name.admin_order_field = "business__name"

    def branch_name(self, obj):
        return obj.branch.name if obj.branch_id else "-"

    branch_name.short_description = "Branch"
    branch_name.admin_order_field = "branch__name"

    def amount_display(self, obj):
        color = "#dc3545" if obj.total_paid_amount < 0 else "#28a745"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.total_paid_amount,
        )

    amount_display.short_description = "Amount"
    amount_display.admin_order_field = "total_paid_amount"

    def payment_method_name(self, obj):
        return obj.payment_method.display_name if obj.payment_method_id else "-"

    payment_method_name.short_description = "Payment Method"

    def created_by_email(self, obj):
        return obj.created_by.email if obj.created_by_id else "-"

    created_by_email.short_description = "Created By"

    def order_info(self, obj):
        if obj.order:
            order_id_short = str(obj.order.id)[:8] + "..."
            url = reverse("admin:orders_order_change", args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, order_id_short)
        return "-"

    order_info.short_description = "Order"


@admin.action(description="Export financial summary")
def export_financial_summary(modeladmin, request, queryset):
    # This would typically generate a report or CSV
    # For now, we'll just show a message
    from django.contrib import messages

    total_sales = sum(t.total_paid_amount for t in queryset if t.type == "SALE")
    total_expenses = sum(t.total_paid_amount for t in queryset if t.type == "EXPENSE")

    messages.success(
        request,
        f"Summary: ${total_sales} in sales, ${total_expenses} in expenses from {queryset.count()} transactions",
    )


# Add actions to TransactionAdmin
TransactionAdmin.actions = [export_financial_summary]
