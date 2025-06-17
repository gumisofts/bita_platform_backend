from django.contrib import admin

from .models import *


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = [
        "movement_number",
        "from_branch",
        "to_branch",
        "status",
        "requested_by",
        "created_at",
    ]
    list_filter = ["status", "created_at", "business"]
    search_fields = ["movement_number", "from_branch__name", "to_branch__name"]
    readonly_fields = [
        "movement_number",
        "approved_by",
        "shipped_by",
        "received_by",
        "approved_at",
        "shipped_at",
        "received_at",
    ]
    ordering = ["-created_at"]


@admin.register(InventoryMovementItem)
class InventoryMovementItemAdmin(admin.ModelAdmin):
    list_display = [
        "movement",
        "supplied_item",
        "quantity_requested",
        "quantity_shipped",
        "quantity_received",
    ]
    list_filter = ["movement__status", "movement__created_at"]
    search_fields = ["movement__movement_number", "supplied_item__item__name"]
