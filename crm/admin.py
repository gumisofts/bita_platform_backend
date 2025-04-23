from django.contrib import admin
from .models import *


class CustomerAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "created_at")
    ordering = ("-created_at",)


class GiftCardAdmin(admin.ModelAdmin):
    list_display = ("id", "created_by", "issued_by",
                    "current_owner", "expires_at", "status")
    ordering = ('-created_at',)


class GiftCardTransferAdmin(admin.ModelAdmin):
    list_display = ("gift_card", 'from_customer', "to_customer")
    ordering = ('-created_at',)


admin.site.register(Customer, CustomerAdmin)
admin.site.register(GiftCard, GiftCardAdmin)
admin.site.register(GiftCardTransfer, GiftCardTransferAdmin)
