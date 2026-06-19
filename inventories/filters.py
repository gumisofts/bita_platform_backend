from django.db.models import F, Q, Sum
from django_filters import (
    BooleanFilter,
    CharFilter,
    DateFilter,
    FilterSet,
    IsoDateTimeFilter,
    ModelChoiceFilter,
    ModelMultipleChoiceFilter,
    NumberFilter,
    RangeFilter,
)

from business.models import Category

from .models import *


class ItemFilter(FilterSet):
    branch = CharFilter(field_name="branch_id", lookup_expr="exact")
    branch_id = CharFilter(field_name="branch_id", lookup_expr="exact")
    business = CharFilter(field_name="business_id", lookup_expr="exact")
    business_id = CharFilter(field_name="business_id", lookup_expr="exact")
    low_stock = BooleanFilter(method="filter_low_stock")
    search = CharFilter(method="filter_search")
    updated_since = IsoDateTimeFilter(method="filter_updated_since")

    class Meta:
        model = Item
        fields = [
            "name",
            "description",
            "group",
            "categories",
            "inventory_unit",
        ]

    def filter_updated_since(self, queryset, name, value):
        """
        Items that changed at/after ``value`` (an ISO-8601 timestamp).

        Mirrors ``ItemVariantFilter.updated_since`` but rooted at the item: an
        item is considered updated when the item row itself OR any of its
        variants OR any related record carrying variant info was touched on/after
        the timestamp. This covers restocks (SuppliedItem / Supply), price-tier
        changes (Pricing), variant attributes (Property), returns (ReturnRecall)
        and inter-branch movements (InventoryMovementItem), so a sync client can
        pull only the items that actually changed.

        Send an ISO-8601 timestamp, ideally timezone-aware
        (e.g. ``2026-06-01T00:00:00Z``), so the comparison is unambiguous.
        """
        return queryset.filter(
            Q(updated_at__gte=value)
            | Q(variants__updated_at__gte=value)
            | Q(variants__supplied_items__updated_at__gte=value)
            | Q(variants__supplied_items__supply__updated_at__gte=value)
            | Q(variants__pricings__updated_at__gte=value)
            | Q(variants__properties__updated_at__gte=value)
            | Q(variants__returnrecall__updated_at__gte=value)
            | Q(variants__inventorymovementitem__updated_at__gte=value)
        ).distinct()

    def filter_search(self, queryset, name, value):
        """Free-text search across item name/description and its variants."""
        value = (value or "").strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(group__name__icontains=value)
            | Q(variants__name__icontains=value)
            | Q(variants__sku__icontains=value)
        ).distinct()

    def filter_low_stock(self, queryset, name, value):
        """
        When value=True: items whose total supplied quantity across all variants
        is at or below their notify_below threshold, or items with no stock at all.
        When value=False: exclude those items.
        """
        annotated = queryset.annotate(
            total_supplied_qty=Sum("variants__supplied_items__quantity")
        )
        condition = Q(total_supplied_qty__lte=F("notify_below")) | Q(
            total_supplied_qty__isnull=True
        )
        if value:
            return annotated.filter(condition)
        return annotated.exclude(condition)


class ItemVariantFilter(FilterSet):
    sku = CharFilter(field_name="sku", lookup_expr="icontains")
    selling_price = RangeFilter(field_name="selling_price")
    name = CharFilter(field_name="name", lookup_expr="icontains")
    item = ModelChoiceFilter(field_name="item", queryset=Item.objects.all())
    item__name = CharFilter(field_name="item__name", lookup_expr="icontains")
    item__description = CharFilter(
        field_name="item__description", lookup_expr="icontains"
    )
    item__group = ModelChoiceFilter(
        field_name="item__group", queryset=Group.objects.all()
    )
    item__group__name = CharFilter(
        field_name="item__group__name", lookup_expr="icontains"
    )
    item__categories = ModelChoiceFilter(
        field_name="item__categories", queryset=Category.objects.all()
    )
    branch = CharFilter(field_name="item__branch_id", lookup_expr="exact")
    branch_id = CharFilter(field_name="item__branch_id", lookup_expr="exact")
    business = CharFilter(field_name="item__business_id", lookup_expr="exact")
    business_id = CharFilter(field_name="item__business_id", lookup_expr="exact")
    low_stock = BooleanFilter(method="filter_low_stock")
    expiring = BooleanFilter(method="filter_expiring")
    quantity_lte = NumberFilter(method="filter_quantity_lte")
    expire_date_lte = DateFilter(method="filter_expire_date_lte")
    updated_since = IsoDateTimeFilter(method="filter_updated_since")

    class Meta:
        model = ItemVariant
        fields = ["name", "item", "selling_price", "sku"]

    def filter_low_stock(self, queryset, name, value):
        """
        When value=True: variants whose total supplied quantity (sum of all
        SuppliedItem.quantity for that variant) is <= item.notify_below.
        When value=False: exclude those variants.
        """
        annotated = queryset.annotate(
            total_supplied_qty=Sum("supplied_items__quantity")
        )
        condition = Q(total_supplied_qty__lte=F("item__notify_below")) | Q(
            total_supplied_qty__isnull=True
        )
        if value:
            return annotated.filter(condition)
        return annotated.exclude(condition)

    def filter_expiring(self, queryset, name, value):
        """
        When value=True: variants that have at least one SuppliedItem with a
        non-null expire_date and quantity > 0.
        When value=False: exclude those variants.
        """
        has_expiring = Q(
            supplied_items__expire_date__isnull=False,
            supplied_items__quantity__gt=0,
        )
        if value:
            return queryset.filter(has_expiring).distinct()
        return queryset.exclude(id__in=queryset.filter(has_expiring).values("id"))

    def filter_quantity_lte(self, queryset, name, value):
        """
        Variants whose total supplied quantity (sum of all SuppliedItem.quantity)
        is <= value, including variants with no supplied items (treated as 0).
        """
        return queryset.annotate(
            total_supplied_qty=Sum("supplied_items__quantity")
        ).filter(Q(total_supplied_qty__lte=value) | Q(total_supplied_qty__isnull=True))

    def filter_expire_date_lte(self, queryset, name, value):
        """
        Variants that have at least one SuppliedItem whose expire_date is on or
        before the given date.
        """
        return queryset.filter(
            supplied_items__expire_date__isnull=False,
            supplied_items__expire_date__lte=value,
        ).distinct()

    def filter_updated_since(self, queryset, name, value):
        """
        Variants that changed at/after ``value`` (an ISO-8601 timestamp).

        "Changed" is intentionally broad: a variant is considered updated when
        the variant row itself OR any related record that carries variant info
        was touched on/after the timestamp. This covers updates that never land
        on the ItemVariant model directly, such as:
          - restocking / new supply batches (SuppliedItem) and the parent
            Supply (supplier, payment, totals)
          - price-tier changes (Pricing)
          - variant attributes (Property)
          - returns / recalls (ReturnRecall)
          - inter-branch inventory movements (InventoryMovementItem)
          - the parent Item (name, group, flags, reorder point, ...)

        Send an ISO-8601 timestamp, ideally timezone-aware
        (e.g. ``2026-06-01T00:00:00Z``), so the comparison is unambiguous.
        """
        return queryset.filter(
            Q(updated_at__gte=value)
            | Q(item__updated_at__gte=value)
            | Q(supplied_items__updated_at__gte=value)
            | Q(supplied_items__supply__updated_at__gte=value)
            | Q(pricings__updated_at__gte=value)
            | Q(properties__updated_at__gte=value)
            | Q(returnrecall__updated_at__gte=value)
            | Q(inventorymovementitem__updated_at__gte=value)
        ).distinct()


class GroupFilter(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    description = CharFilter(field_name="description", lookup_expr="icontains")
    business = CharFilter(field_name="business_id", lookup_expr="exact")
    business_id = CharFilter(field_name="business_id", lookup_expr="exact")

    class Meta:
        model = Group
        fields = ["name", "description"]


class SupplierFilter(FilterSet):
    email = CharFilter(field_name="email", lookup_expr="icontains")
    phone_number = CharFilter(field_name="phone_number", lookup_expr="icontains")
    name = CharFilter(field_name="name", lookup_expr="icontains")
    business = CharFilter(field_name="business_id", lookup_expr="exact")
    business_id = CharFilter(field_name="business_id", lookup_expr="exact")
    search = CharFilter(method="filter_search")

    class Meta:
        model = Supplier
        fields = ["name", "email", "phone_number"]

    def filter_search(self, queryset, name, value):
        """Free-text search across supplier name, phone, and email."""
        value = (value or "").strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(phone_number__icontains=value)
            | Q(email__icontains=value)
        )


class SupplyFilter(FilterSet):
    label = CharFilter(field_name="label", lookup_expr="icontains")
    branch = CharFilter(field_name="branch_id", lookup_expr="exact")
    branch_id = CharFilter(field_name="branch_id", lookup_expr="exact")
    business = CharFilter(field_name="business_id", lookup_expr="exact")
    business_id = CharFilter(field_name="business_id", lookup_expr="exact")

    class Meta:
        model = Supply
        fields = ["label"]


class SuppliedItemFilter(FilterSet):
    supply = CharFilter(field_name="supply_id", lookup_expr="exact")
    supply_id = CharFilter(field_name="supply_id", lookup_expr="exact")
    branch = CharFilter(field_name="supply__branch_id", lookup_expr="exact")
    branch_id = CharFilter(field_name="supply__branch_id", lookup_expr="exact")
    business = CharFilter(field_name="business_id", lookup_expr="exact")
    business_id = CharFilter(field_name="business_id", lookup_expr="exact")
    variant = CharFilter(field_name="variant_id", lookup_expr="exact")
    item = CharFilter(field_name="item_id", lookup_expr="exact")
    expire_date = CharFilter(field_name="expire_date", lookup_expr="exact")
    expire_date_before = CharFilter(field_name="expire_date", lookup_expr="lte")
    expire_date_after = CharFilter(field_name="expire_date", lookup_expr="gte")
    batch_number = CharFilter(field_name="batch_number", lookup_expr="icontains")

    class Meta:
        model = SuppliedItem
        fields = ["supply", "variant", "item", "business"]
