from django_filters import CharFilter, FilterSet, ModelChoiceFilter, ModelMultipleChoiceFilter, RangeFilter

from .models import *
from business.models import Category


class ItemFilter(FilterSet):
    class Meta:
        model = Item
        fields = [
            "name",
            "description",
            "business",
            "group",
            "categories",
            "inventory_unit",
            "branch",
        ]


class ItemVariantFilter(FilterSet):
    sku = CharFilter(field_name="sku", lookup_expr="icontains")
    selling_price = RangeFilter(field_name="selling_price")
    name = CharFilter(field_name="name", lookup_expr="icontains")
    item = ModelChoiceFilter(field_name="item", queryset=Item.objects.all())
    item__name = CharFilter(field_name="item__name", lookup_expr="icontains")
    item__description = CharFilter(field_name="item__description", lookup_expr="icontains")
    item__group = ModelChoiceFilter(field_name="item__group", queryset=Group.objects.all())
    item__group__name = CharFilter(field_name="item__group__name", lookup_expr="icontains")
    item__categories = ModelChoiceFilter(field_name="item__categories", queryset=Category.objects.all())
    

    class Meta:
        model = ItemVariant
        fields = ["name", "item", "selling_price", "sku"]


class GroupFilter(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    description = CharFilter(field_name="description", lookup_expr="icontains")
    class Meta:
        model = Group
        fields = ["name", "description", "business"]

class SupplierFilter(FilterSet):
    email = CharFilter(field_name="email", lookup_expr="icontains")
    phone_number = CharFilter(field_name="phone_number", lookup_expr="icontains")
    name = CharFilter(field_name="name", lookup_expr="icontains")
    class Meta:
        model = Supplier
        fields = ["name", "email", "phone_number", "business"]