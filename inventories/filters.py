from django_filters import FilterSet, ModelChoiceFilter, RangeFilter

from .models import Group, Item, ItemVariant


class ItemFilter(FilterSet):
    class Meta:
        model = Item
        fields = ["name", "description","business","group", "categories", "inventory_unit", "branch"]
        
class ItemVariantFilter(FilterSet):
    selling_price = RangeFilter(field_name="selling_price")
    class Meta:
        model = ItemVariant
        fields = ["name", "item", "selling_price", "expire_date", "man_date","sku"]
        
        
       
class GroupFilter(FilterSet):
    class Meta:
        model = Group
        fields = ["name", "description", "business"]