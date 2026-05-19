from django_filters import FilterSet

from finances.models import BusinessPaymentMethod


class BusinessPaymentMethodFilter(FilterSet):
    class Meta:
        model = BusinessPaymentMethod
        fields = ["business", "branch", "payment"]
