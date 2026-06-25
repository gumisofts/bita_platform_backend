from django.contrib import admin

from .models import (
    MarketplaceOrder,
    MarketplaceOrderItem,
    Review,
    VariantImage,
    Waitlist,
)


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "business_name", "phone", "created_at"]
    search_fields = ["email", "full_name", "business_name"]
    ordering = ["-created_at"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "rating",
        "reviewer_name",
        "business",
        "variant",
        "is_verified_purchase",
        "created_at",
    ]
    list_filter = ["rating", "is_verified_purchase"]
    search_fields = ["reviewer_name", "title", "body"]
    raw_id_fields = ["reviewer", "business", "variant"]
    ordering = ["-created_at"]


class MarketplaceOrderItemInline(admin.TabularInline):
    model = MarketplaceOrderItem
    extra = 0
    raw_id_fields = ["variant"]


@admin.register(MarketplaceOrder)
class MarketplaceOrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "business",
        "buyer_name",
        "buyer_email",
        "status",
        "total_payable",
        "created_at",
    ]
    list_filter = ["status"]
    search_fields = ["buyer_name", "buyer_email", "buyer_phone"]
    raw_id_fields = ["business"]
    inlines = [MarketplaceOrderItemInline]
    ordering = ["-created_at"]


@admin.register(VariantImage)
class VariantImageAdmin(admin.ModelAdmin):
    list_display = ["variant", "is_primary", "is_thumbnail", "is_visible"]
    raw_id_fields = ["variant", "file"]
