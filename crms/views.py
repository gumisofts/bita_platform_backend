from rest_framework import viewsets

from .models import Customer, GiftCard
from .serializers import *


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


# class GiftCardViewSet(viewsets.ModelViewSet):
#     queryset = GiftCard.objects.all()
#     serializer_class = GiftCardSerializer


# class GiftCardTransactionViewSet(viewsets.ModelViewSet):
#     queryset = GiftCardTransaction.objects.all()
#     serializer_class = GiftCardTransactionSerializer
