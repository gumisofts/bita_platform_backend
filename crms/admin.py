from django.contrib import admin

from .models import Customer, GiftCard

# class GiftCardTransactionInline(admin.TabularInline):
#     model = GiftCardTransaction
#     extra = 0


class CustomerAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "created_at")
    ordering = ("-created_at",)


# class GiftCardAdmin(admin.ModelAdmin):
#     list_display = ('code', 'customer', 'original_value',
#                     'remaining_value', 'status')
#     inlines = [GiftCardTransactionInline]


class GiftCardTransactionAdmin(admin.ModelAdmin):
    list_display = ("gift_card", "amount", "created_at")


admin.site.register(Customer, CustomerAdmin)
# admin.site.register(GiftCard, GiftCardAdmin)
# admin.site.register(GiftCardTransaction, GiftCardTransactionAdmin)
