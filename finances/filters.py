from django_filters import CharFilter, FilterSet

from finances.models import BusinessPaymentMethod, Transaction


class TransactionFilter(FilterSet):
    type = CharFilter(field_name="type", lookup_expr="exact")
    payment_method__identifier = CharFilter(
        field_name="payment_method__identifier", lookup_expr="iexact"
    )
    category = CharFilter(field_name="category", lookup_expr="exact")

    class Meta:
        model = Transaction
        fields = ["type", "payment_method__identifier", "category"]


class BusinessPaymentMethodFilter(FilterSet):
    model = BusinessPaymentMethod
    fields = ["business", "payment"]
