from django_filters import FilterSet

from finances.models import BusinessPaymentMethod


class BusinPaymentMethodFilter(FilterSet):
    class Meta:
        model = BusinessPaymentMethod
        fields = ["business", "branch", "payment"]
