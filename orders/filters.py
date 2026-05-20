from django_filters import CharFilter, DateFilter, FilterSet, NumberFilter

from orders.models import Order


class OrderFilter(FilterSet):
    branch = CharFilter(field_name="branch_id", lookup_expr="iexact")
    branch_id = CharFilter(field_name="branch_id", lookup_expr="iexact")
    business = CharFilter(field_name="business_id", lookup_expr="iexact")
    business_id = CharFilter(field_name="business_id", lookup_expr="iexact")

    employee = CharFilter(field_name="employee_id", lookup_expr="iexact")
    customer = CharFilter(field_name="customer_id", lookup_expr="iexact")
    payment_method = CharFilter(field_name="payment_method_id", lookup_expr="iexact")

    created_after = DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = DateFilter(field_name="created_at", lookup_expr="date__lte")

    total_min = NumberFilter(field_name="total_payable", lookup_expr="gte")
    total_max = NumberFilter(field_name="total_payable", lookup_expr="lte")

    class Meta:
        model = Order
        fields = ["status"]
