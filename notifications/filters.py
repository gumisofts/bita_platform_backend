from django_filters import FilterSet, DateFilter

from .models import Notification


class NotificationFilter(FilterSet):
    timestamp = DateFilter(field_name="created_at", lookup_expr="gte")
    class Meta:
        model = Notification
        fields = ["notification_type", "delivery_method", "created_at",'timestamp']