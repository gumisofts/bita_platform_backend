from django.db.models import F, Q, Sum
from django_filters import (
    BooleanFilter,
    CharFilter,
    FilterSet,
    ModelChoiceFilter,
    ModelMultipleChoiceFilter,
    RangeFilter,
)

from business.models import Category

from .models import *


class ItemFilter(FilterSet):
    branch = CharFilter(field_name="branch_id", lookup_expr="exact")
    branch_id = CharFilter(field_name="branch_id", lookup_expr="exact")
    business = CharFilter(field_name="business_id", lookup_expr="exact")
    business_id = CharFilter(field_name="business_id", lookup_expr="exact")

    class Meta:
        model = Item
        fields = [
            "name",
            "description",
            "group",
            "categories",
            "inventory_unit",
        ]


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

    class Meta:
        model = Supplier
        fields = ["name", "email", "phone_number"]


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
