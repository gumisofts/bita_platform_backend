from rest_framework import viewsets
from .models import Customer, GiftCard
from .serializers import CustomerSerializer, GiftCardSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class GiftCardViewSet(viewsets.ModelViewSet):
    queryset = GiftCard.objects.all()
    serializer_class = GiftCardSerializer
