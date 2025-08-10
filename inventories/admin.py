from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import *


class PropertyInline(admin.TabularInline):
    model = Property
    extra = 0
    fields = ("name", "value")
    fk_name = "item_variant"


class ItemInline(admin.TabularInline):
    model = Item
    extra = 0
    fields = ("name", "inventory_unit", "min_selling_quota")
    readonly_fields = ("created_at",)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "business_name", "item_count", "created_at"]
    list_filter = ["business", "created_at"]
    search_fields = ["name", "description", "business__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["business"]
    inlines = [ItemInline]

    fieldsets = (
        (None, {"fields": ("id", "name", "business")}),
        (_("Details"), {"fields": ("description",)}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def business_name(self, obj):
        return obj.business.name if obj.business else "-"

    business_name.short_description = "Business"

    def item_count(self, obj):
        count = obj.items.count()
        return f"{count} items"

    item_count.short_description = "Items"


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "business_name",
        "group_name",
        "inventory_unit",
        "min_selling_quota",
        "category_list",
        "created_at",
    ]
    list_filter = ["business", "group", "inventory_unit", "categories", "created_at"]
    search_fields = ["name", "description", "business__name", "group__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["business", "group"]
    filter_horizontal = ["categories"]
    # inlines = [PropertyInline]  # Property is related to ItemVariant, not Item

    fieldsets = (
        (None, {"fields": ("id", "name", "business", "group")}),
        (
            _("Details"),
            {"fields": ("description", "inventory_unit", "min_selling_quota")},
        ),
        (_("Categories"), {"fields": ("categories",), "classes": ("collapse",)}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def business_name(self, obj):
        return obj.business.name if obj.business else "-"

    business_name.short_description = "Business"

    def group_name(self, obj):
        return obj.group.name if obj.group else "-"

    group_name.short_description = "Group"

    def category_list(self, obj):
        categories = obj.categories.all()[:3]  # Show first 3 categories
        if not categories:
            return "-"
        names = [cat.name for cat in categories]
        result = ", ".join(names)
        if obj.categories.count() > 3:
            result += f" (+{obj.categories.count() - 3} more)"
        return result

    category_list.short_description = "Categories"


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "value", "item_variant_name", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "value", "item_variant__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["item_variant"]

    fieldsets = (
        (None, {"fields": ("id", "item_variant", "name", "value")}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def item_variant_name(self, obj):
        return obj.item_variant.name if obj.item_variant else "-"

    item_variant_name.short_description = "Item Variant"


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


# Additional admin configurations for any other inventory models
try:
    from .models import SuppliedItem

    @admin.register(SuppliedItem)
    class SuppliedItemAdmin(admin.ModelAdmin):
        list_display = [
            "id",
            "item_name",
            "purchase_price",
            "quantity",
            "created_at",
        ]
        list_filter = ["created_at", "item__business"]
        search_fields = [
            "item__name",
            "supply__label",
            "supply__branch__name",
            "supply__supplier__name",
            "supply__supplier__email",
        ]
        readonly_fields = ["id", "created_at", "updated_at"]
        raw_id_fields = ["item", "supply"]

        fieldsets = (
            (None, {"fields": ("id", "item", "purchase_price", "quantity")}),
            (
                _("Product Details"),
                {
                    "fields": (
                        "batch_number",
                        "product_number",
                        "expire_date",
                        "man_date",
                    )
                },
            ),
            (
                _("Business & Supplier"),
                {
                    "fields": ("business", "supply"),
                    "classes": ("collapse",),
                },
            ),
            (
                _("Timestamps"),
                {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
            ),
        )

        def item_name(self, obj):
            return obj.item.name if obj.item else "-"

        item_name.short_description = "Item"

except ImportError:
    # SuppliedItem model doesn't exist
    pass


try:
    from .models import ItemVariant

    @admin.register(ItemVariant)
    class ItemVariantAdmin(admin.ModelAdmin):
        list_display = [
            "id",
            "name",
            "item_name",
            "quantity",
            "selling_price",
            "property_count",
            "created_at",
        ]
        list_filter = ["item", "created_at"]
        search_fields = ["name", "item__name", "sku"]
        readonly_fields = ["id", "created_at", "updated_at"]
        raw_id_fields = ["item"]
        inlines = [PropertyInline]

        fieldsets = (
            (None, {"fields": ("id", "name", "item", "quantity", "selling_price")}),
            (
                _("Product Details"),
                {"fields": ("sku",)},
            ),
            (
                _("Settings"),
                {
                    "fields": ("is_default",),
                    "classes": ("collapse",),
                },
            ),
            (
                _("Timestamps"),
                {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
            ),
        )

        def item_name(self, obj):
            return obj.item.name if obj.item else "-"

        item_name.short_description = "Item"

        def property_count(self, obj):
            count = obj.properties.count()
            return f"{count} properties"

        property_count.short_description = "Properties"

except ImportError:
    # ItemVariant model doesn't exist
    pass


try:
    from .models import ItemImage, Supplier, Supply

    @admin.register(Supplier)
    class SupplierAdmin(admin.ModelAdmin):
        list_display = [
            "id",
            "name",
            "email",
            "phone_number",
            "business_name",
            "created_at",
        ]
        list_filter = ["business", "created_at"]
        search_fields = ["name", "email", "phone_number", "business__name"]
        readonly_fields = ["id", "created_at", "updated_at"]
        raw_id_fields = ["business"]

        def business_name(self, obj):
            return obj.business.name if obj.business else "-"

        business_name.short_description = "Business"

    @admin.register(Supply)
    class SupplyAdmin(admin.ModelAdmin):
        list_display = ["id", "label", "branch_name", "created_at"]
        list_filter = ["branch", "created_at"]
        search_fields = ["label", "branch__name"]
        readonly_fields = ["id", "created_at", "updated_at"]
        raw_id_fields = ["branch"]

        def branch_name(self, obj):
            return obj.branch.name if obj.branch else "-"

        branch_name.short_description = "Branch"

    @admin.register(ItemImage)
    class ItemImageAdmin(admin.ModelAdmin):
        list_display = [
            "id",
            "item_name",
            "is_primary",
            "is_visible",
            "is_thumbnail",
            "created_at",
        ]
        list_filter = ["is_primary", "is_visible", "is_thumbnail", "created_at"]
        search_fields = ["item__name"]
        readonly_fields = ["id", "created_at", "updated_at"]
        raw_id_fields = ["item", "file"]

        def item_name(self, obj):
            return obj.item.name if obj.item else "-"

        item_name.short_description = "Item"

except ImportError:
    # Models don't exist
    pass
