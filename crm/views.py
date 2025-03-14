from rest_framework import viewsets

from .models import Customer, GiftCard
from .serializers import CustomerSerializer, GiftCardSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def get_queryset(self):
        queryset = self.queryset
        business = self.request.query_params.get("business", None)
        if business is not None:
            queryset = queryset.filter(business=business)
        return queryset


class GiftCardViewSet(viewsets.ModelViewSet):
    queryset = GiftCard.objects.all()
    serializer_class = GiftCardSerializer

    def get_queryset(self):
        queryset = self.queryset
        business = self.request.query_params.get("business", None)
        if business is not None:
            queryset = queryset.filter(business=business)
        owner = self.request.query_params.get("owner", None)
        if owner is not None:
            queryset = queryset.filter(owner=owner)
        creator = self.request.query_params.get("creator", None)
        if creator is not None:
            queryset = queryset.filter(created_by=creator)
        redeemed = self.request.query_params.get("redeemed", None)
        if redeemed is not None:
            if redeemed == "true":
                queryset = queryset.filter(redeemed=True)
            else:
                queryset = queryset.filter(redeemed=False)
        type = self.request.query_params.get("type", None)
        if type is not None:
            queryset = queryset.filter(type=type)
        return queryset
