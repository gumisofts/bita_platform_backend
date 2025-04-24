from rest_framework import viewsets

from .models import Customer, GiftCard, GiftCardTransfer
from .serializers import (
    CustomerSerializer,
    GiftCardSerializer,
    GiftCardTransferSerializer,
)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = []


class GiftCardViewSet(viewsets.ModelViewSet):
    queryset = GiftCard.objects.all()
    serializer_class = GiftCardSerializer
    permission_classes = []


class GiftCardTransferViewSet(viewsets.ModelViewSet):
    queryset = GiftCardTransfer.objects.all()
    serializer_class = GiftCardTransferSerializer
    permission_classes = []
