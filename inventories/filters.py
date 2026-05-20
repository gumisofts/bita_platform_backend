from django_filters import (
    CharFilter,
    FilterSet,
    ModelChoiceFilter,
    ModelMultipleChoiceFilter,
    RangeFilter,
)

from business.models import Category

from .models import *


class ItemFilter(FilterSet):
    branch = CharFilter(field_name="branch_id", lookup_expr="iexact")
    branch_id = CharFilter(field_name="branch_id", lookup_expr="iexact")
    business = CharFilter(field_name="business_id", lookup_expr="iexact")
    business_id = CharFilter(field_name="business_id", lookup_expr="iexact")

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
    branch = CharFilter(field_name="item__branch_id", lookup_expr="iexact")
    branch_id = CharFilter(field_name="item__branch_id", lookup_expr="iexact")
    business = CharFilter(field_name="item__business_id", lookup_expr="iexact")
    business_id = CharFilter(field_name="item__business_id", lookup_expr="iexact")

    class Meta:
        model = ItemVariant
        fields = ["name", "item", "selling_price", "sku"]


class GroupFilter(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    description = CharFilter(field_name="description", lookup_expr="icontains")
    business = CharFilter(field_name="business_id", lookup_expr="iexact")
    business_id = CharFilter(field_name="business_id", lookup_expr="iexact")

    class Meta:
        model = Group
        fields = ["name", "description"]


class SupplierFilter(FilterSet):
    email = CharFilter(field_name="email", lookup_expr="icontains")
    phone_number = CharFilter(field_name="phone_number", lookup_expr="icontains")
    name = CharFilter(field_name="name", lookup_expr="icontains")
    business = CharFilter(field_name="business_id", lookup_expr="iexact")
    business_id = CharFilter(field_name="business_id", lookup_expr="iexact")

    class Meta:
        model = Supplier
        fields = ["name", "email", "phone_number"]


class SupplyFilter(FilterSet):
    label = CharFilter(field_name="label", lookup_expr="icontains")
    branch = CharFilter(field_name="branch_id", lookup_expr="iexact")
    branch_id = CharFilter(field_name="branch_id", lookup_expr="iexact")
    business = CharFilter(field_name="business_id", lookup_expr="iexact")
    business_id = CharFilter(field_name="business_id", lookup_expr="iexact")

    class Meta:
        model = Supply
        fields = ["label"]
