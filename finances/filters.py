import django_filters
from django.db import models
from django_filters import FilterSet

from finances.models import BusinessPaymentMethod


class BusinessPaymentMethodFilter(FilterSet):
    branch = django_filters.UUIDFilter(method="filter_branch")

    class Meta:
        model = BusinessPaymentMethod
        fields = ["business", "branch", "payment"]

    def filter_branch(self, queryset, name, value):
        print(name, value)
        return queryset.filter(models.Q(branch=value) | models.Q(branch__isnull=True))
