from django_filters import FilterSet

from orders.models import Order


class OrderFilter(FilterSet):
    class Meta:
        model = Order
        fields = ["status", "business", "branch"]
