from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import *


class GiftCardTransferInline(admin.TabularInline):
    model = GiftCardTransfer
    extra = 0
    fields = ("from_customer", "to_customer", "created_at")
    readonly_fields = ("created_at",)
    fk_name = "gift_card"


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "full_name",
        "phone_number",
        "business_name",
        "gift_card_count",
        "created_at",
    )
    list_filter = ("business", "created_at")
    search_fields = ("email", "full_name", "phone_number", "business__name")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("business",)

    fieldsets = (
        (None, {"fields": ("id", "full_name", "business")}),
        (_("Contact Information"), {"fields": ("email", "phone_number")}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def business_name(self, obj):
        return obj.business.name if obj.business else "-"

    business_name.short_description = "Business"

    def gift_card_count(self, obj):
        count = obj.owned_giftcards.count()
        return f"{count} gift cards"

    gift_card_count.short_description = "Gift Cards"


@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "value",
        "status_colored",
        "card_type",
        "created_by_info",
        "issued_by_info",
        "current_owner_info",
        "expires_at",
        "created_at",
    )
    list_filter = ("status", "card_type", "created_at", "expires_at")
    search_fields = (
        "created_by__email",
        "issued_by__email",
        "current_owner__email",
        "current_owner__full_name",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("created_by", "issued_by", "current_owner")
    filter_horizontal = ("products",)
    inlines = [GiftCardTransferInline]

    fieldsets = (
        (None, {"fields": ("id", "value", "status", "card_type")}),
        (_("People"), {"fields": ("created_by", "issued_by", "current_owner")}),
        (_("Products"), {"fields": ("products",), "classes": ("collapse",)}),
        (
            _("Dates"),
            {
                "fields": ("expires_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def status_colored(self, obj):
        colors = {
            "new": "#6c757d",  # Gray
            "active": "#28a745",  # Green
            "issued": "#17a2b8",  # Blue
            "redeemed": "#ffc107",  # Yellow
            "expired": "#dc3545",  # Red
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_colored.short_description = "Status"

    def created_by_info(self, obj):
        if obj.created_by:
            return f"{obj.created_by.email} ({obj.created_by.first_name} {obj.created_by.last_name})"
        return "-"

    created_by_info.short_description = "Created By"

    def issued_by_info(self, obj):
        if obj.issued_by:
            return f"{obj.issued_by.email} ({obj.issued_by.first_name} {obj.issued_by.last_name})"
        return "-"

    issued_by_info.short_description = "Issued By"

    def current_owner_info(self, obj):
        if obj.current_owner:
            return f"{obj.current_owner.email} ({obj.current_owner.full_name})"
        return "-"

    current_owner_info.short_description = "Current Owner"


@admin.register(GiftCardTransfer)
class GiftCardTransferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "gift_card_value",
        "from_customer_info",
        "to_customer_info",
        "created_at",
    )
    list_filter = ("created_at", "gift_card__status", "gift_card__card_type")
    search_fields = (
        "gift_card__id",
        "from_customer__email",
        "from_customer__full_name",
        "to_customer__email",
        "to_customer__full_name",
    )
    readonly_fields = ("id", "created_at")
    raw_id_fields = ("gift_card", "from_customer", "to_customer")

    fieldsets = (
        (None, {"fields": ("id", "gift_card")}),
        (_("Transfer Details"), {"fields": ("from_customer", "to_customer")}),
        (_("Timestamps"), {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def gift_card_value(self, obj):
        return f"${obj.gift_card.value}" if obj.gift_card else "-"

    gift_card_value.short_description = "Gift Card Value"

    def from_customer_info(self, obj):
        if obj.from_customer:
            return f"{obj.from_customer.email} ({obj.from_customer.full_name})"
        return "-"

    from_customer_info.short_description = "From"

    def to_customer_info(self, obj):
        if obj.to_customer:
            return f"{obj.to_customer.email} ({obj.to_customer.full_name})"
        return "-"

    to_customer_info.short_description = "To"


# Custom admin actions
@admin.action(description="Mark selected gift cards as active")
def mark_gift_cards_active(modeladmin, request, queryset):
    queryset.update(status="active")


@admin.action(description="Mark selected gift cards as expired")
def mark_gift_cards_expired(modeladmin, request, queryset):
    queryset.update(status="expired")


# Add actions to GiftCardAdmin
GiftCardAdmin.actions = [mark_gift_cards_active, mark_gift_cards_expired]
