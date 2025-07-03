from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from financials.models import *


class BusinessPaymentMethodInline(admin.TabularInline):
    model = BusinessPaymentMethod
    extra = 0
    fields = ('payment', 'label', 'identifier')
    raw_id_fields = ('payment',)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "short_name", "image_preview", "business_count", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "short_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'short_name')
        }),
        (_('Media'), {
            'fields': ('image',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = "Image"
    
    def business_count(self, obj):
        count = obj.businesspaymentmethod_set.count()
        return f"{count} businesses"
    business_count.short_description = "Used by"


@admin.register(BusinessPaymentMethod)
class BusinessPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["id", "business_name", "payment_name", "label", "identifier", "created_at"]
    list_filter = ["business", "payment", "created_at"]
    search_fields = ["business__name", "payment__name", "label", "identifier"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["business", "payment"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'business', 'payment')
        }),
        (_('Configuration'), {
            'fields': ('label', 'identifier')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def business_name(self, obj):
        return obj.business.name if obj.business else "-"
    business_name.short_description = "Business"
    
    def payment_name(self, obj):
        return obj.payment.name if obj.payment else "-"
    payment_name.short_description = "Payment Method"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "id", 
        "type_colored", 
        "order_info", 
        "total_paid_amount", 
        "total_left_amount", 
        "payment_status",
        "created_at"
    ]
    list_filter = ["type", "created_at"]
    search_fields = ["order__id", "order__customer_id", "order__employee_id"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["order"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'type', 'order')
        }),
        (_('Financial Details'), {
            'fields': ('total_paid_amount', 'total_left_amount')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def type_colored(self, obj):
        colors = {
            'SALE': '#28a745',      # Green
            'EXPENSE': '#dc3545',   # Red
            'DEBT': '#ffc107',      # Yellow
            'REFUND': '#17a2b8'     # Blue
        }
        color = colors.get(obj.type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_type_display()
        )
    type_colored.short_description = "Type"
    
    def order_info(self, obj):
        if obj.order:
            order_id_short = str(obj.order.id)[:8] + "..."
            return format_html(
                '<a href="/admin/orders/order/{}/change/">{}</a>',
                obj.order.id,
                order_id_short
            )
        return "-"
    order_info.short_description = "Order"
    
    def payment_status(self, obj):
        if obj.total_left_amount == 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">Fully Paid</span>'
            )
        elif obj.total_paid_amount > 0:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">Partially Paid</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Unpaid</span>'
            )
    payment_status.short_description = "Payment Status"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order')


# Custom admin actions
@admin.action(description='Mark selected transactions as fully paid')
def mark_as_fully_paid(modeladmin, request, queryset):
    for transaction in queryset:
        transaction.total_left_amount = 0
        transaction.save()


@admin.action(description='Export financial summary')
def export_financial_summary(modeladmin, request, queryset):
    # This would typically generate a report or CSV
    # For now, we'll just show a message
    from django.contrib import messages
    total_sales = sum(t.total_paid_amount for t in queryset if t.type == 'SALE')
    total_expenses = sum(t.total_paid_amount for t in queryset if t.type == 'EXPENSE')
    
    messages.success(
        request, 
        f"Summary: ${total_sales} in sales, ${total_expenses} in expenses from {queryset.count()} transactions"
    )


# Add actions to TransactionAdmin
TransactionAdmin.actions = [mark_as_fully_paid, export_financial_summary]
