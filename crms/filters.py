from django.db.models import Q
from django_filters import CharFilter, FilterSet

from .models import Customer


class CustomerFilter(FilterSet):
    full_name = CharFilter(field_name="full_name", lookup_expr="icontains")
    email = CharFilter(field_name="email", lookup_expr="icontains")
    phone_number = CharFilter(field_name="phone_number", lookup_expr="icontains")
    business = CharFilter(field_name="business_id", lookup_expr="exact")
    business_id = CharFilter(field_name="business_id", lookup_expr="exact")
    search = CharFilter(method="filter_search")

    class Meta:
        model = Customer
        fields = ["full_name", "email", "phone_number"]

    def filter_search(self, queryset, name, value):
        """Free-text search across customer name, phone, and email."""
        value = (value or "").strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(full_name__icontains=value)
            | Q(phone_number__icontains=value)
            | Q(email__icontains=value)
        )
