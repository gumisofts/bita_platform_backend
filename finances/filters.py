from django_filters import FilterSet

from finances.models import BusinessPaymentMethod


class BusinessPaymentMethodFilter(FilterSet):
    model = BusinessPaymentMethod
    fields = ["business", "payment"]
