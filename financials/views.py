from django.db import transaction as db_transaction
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from inventories.models import SuppliedItem

from .models import BusinessPaymentMethod, Transaction
from .serializers import (
    BusinessPaymentMethodSerializer,
    TransactionSerializer,
)


class TransactionViewset(ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    http_method_names = ["get", "post"]


# CRUD for Business Payment Methods
class BusinessPaymentMethodViewset(ModelViewSet):
    queryset = BusinessPaymentMethod.objects.all()
    serializer_class = BusinessPaymentMethodSerializer

    def get_queryset(self):
        business_id = self.request.query_params.get("business_id")
        if business_id:
            return self.queryset.filter(business_id=business_id)
        return self.queryset


class PaymentMethodViewset(ModelViewSet):
    queryset = BusinessPaymentMethod.objects.all()
    serializer_class = BusinessPaymentMethodSerializer
