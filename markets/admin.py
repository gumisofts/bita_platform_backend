from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from business.models import Category, Industry
from inventories.models import Item, ItemVariant, Property

# Since we're using existing models, we'll create custom admin views for marketplace management

# @admin.register(ItemVariant)
# class MarketplaceItemVariantAdmin(admin.ModelAdmin):
#     """Enhanced admin for marketplace product management"""

#     list_display = [
#         'id', 'name', 'item_name', 'business_name', 'selling_price',
#         'quantity', 'stock_status', 'marketplace_status', 'created_at'
#     ]
#     list_filter = [
#         'is_visible_online', 'receive_online_orders', 'is_default',
#         'item__business__is_verified', 'item__business__business_type',
#         'item__categories', 'created_at'
#     ]
#     search_fields = [
#         'name', 'item__name', 'sku', 'batch_number',
#         'item__business__name', 'item__description'
#     ]
#     readonly_fields = ['id', 'created_at', 'updated_at']
#     raw_id_fields = ['item']

#     fieldsets = (
#         ('Product Information', {
#             'fields': ('id', 'item', 'name', 'selling_price', 'quantity')
#         }),
#         ('Marketplace Settings', {
#             'fields': (
#                 'is_visible_online', 'receive_online_orders',
#                 'is_default', 'is_returnable'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('Product Details', {
#             'fields': ('sku', 'batch_number', 'expire_date', 'man_date'),
#             'classes': ('collapse',)
#         }),
#         ('Stock Management', {
#             'fields': ('notify_below',),
#             'classes': ('collapse',)
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )

#     def item_name(self, obj):
#         return obj.item.name if obj.item else '-'
#     item_name.short_description = 'Item'

#     def business_name(self, obj):
#         return obj.item.business.name if obj.item and obj.item.business else '-'
#     business_name.short_description = 'Business'

#     def stock_status(self, obj):
#         if obj.quantity == 0:
#             return format_html('<span style="color: red;">Out of Stock</span>')
#         elif obj.quantity <= obj.notify_below:
#             return format_html('<span style="color: orange;">Low Stock</span>')
#         else:
#             return format_html('<span style="color: green;">In Stock</span>')
#     stock_status.short_description = 'Stock Status'

#     def marketplace_status(self, obj):
#         if obj.is_visible_online and obj.receive_online_orders and obj.quantity > 0:
#             return format_html('<span style="color: green;">✓ Available</span>')
#         else:
#             return format_html('<span style="color: red;">✗ Not Available</span>')
#     marketplace_status.short_description = 'Marketplace Status'

#     actions = ['make_visible_online', 'make_invisible_online', 'enable_online_orders', 'disable_online_orders']

#     def make_visible_online(self, request, queryset):
#         queryset.update(is_visible_online=True)
#         self.message_user(request, f"{queryset.count()} products made visible online.")
#     make_visible_online.short_description = "Make visible online"

#     def make_invisible_online(self, request, queryset):
#         queryset.update(is_visible_online=False)
#         self.message_user(request, f"{queryset.count()} products made invisible online.")
#     make_invisible_online.short_description = "Make invisible online"

#     def enable_online_orders(self, request, queryset):
#         queryset.update(receive_online_orders=True)
#         self.message_user(request, f"{queryset.count()} products enabled for online orders.")
#     enable_online_orders.short_description = "Enable online orders"

#     def disable_online_orders(self, request, queryset):
#         queryset.update(receive_online_orders=False)
#         self.message_user(request, f"{queryset.count()} products disabled for online orders.")
#     disable_online_orders.short_description = "Disable online orders"


# class MarketplaceCategoryAdmin(admin.ModelAdmin):
#     """Enhanced category admin for marketplace"""

#     list_display = [
#         'name', 'industry_name', 'product_count', 'business_count', 'is_active'
#     ]
#     list_filter = ['is_active', 'industry', 'created_at']
#     search_fields = ['name', 'industry__name']

#     def industry_name(self, obj):
#         return obj.industry.name if obj.industry else '-'
#     industry_name.short_description = 'Industry'

#     def product_count(self, obj):
#         count = ItemVariant.objects.filter(
#             item__categories=obj,
#             is_visible_online=True
#         ).count()
#         return f"{count} products"
#     product_count.short_description = 'Products Online'

#     def business_count(self, obj):
#         count = obj.businesses.filter(is_active=True).count()
#         return f"{count} businesses"
#     business_count.short_description = 'Active Businesses'

# # Only register if not already registered
# try:
#     admin.site.unregister(ItemVariant)
# except admin.sites.NotRegistered:
#     pass
# admin.site.register(ItemVariant, MarketplaceItemVariantAdmin)
