from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from business.permissions import (
    BranchLevelPermission,
    BusinessLevelPermission,
    GuardianObjectPermissions,
)

from .models import Customer, GiftCard, GiftCardTransfer
from .serializers import (
    CustomerSerializer,
    GiftCardSerializer,
    GiftCardTransferSerializer,
)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions,
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        business = self.request.business

        if not business:
            raise ValidationError({"detail": "Empty or invalid business"})

        return queryset.filter(business=business).order_by("-created_at")


class GiftCardViewSet(viewsets.ModelViewSet):
    queryset = GiftCard.objects.all()
    serializer_class = GiftCardSerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions,
    ]


class GiftCardTransferViewSet(viewsets.ModelViewSet):
    queryset = GiftCardTransfer.objects.all()
    serializer_class = GiftCardTransferSerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions,
    ]
