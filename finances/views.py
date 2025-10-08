from django.db import transaction as db_transaction
from guardian.shortcuts import get_objects_for_user
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from business.permissions import (
    AdditionalBusinessPermissionNames,
    BranchLevelPermission,
    BusinessLevelPermission,
    GuardianObjectPermissions,
)
from core.utils import is_valid_uuid
from inventories.models import SuppliedItem

from .models import BusinessPaymentMethod, PaymentMethod, Transaction
from .serializers import (
    BusinessPaymentMethodSerializer,
    PaymentMethodSerializer,
    TransactionSerializer,
)


class TransactionViewset(ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    http_method_names = ["get", "post"]
    permission_classes = [IsAuthenticated]


# CRUD for Business Payment Methods
class BusinessPaymentMethodViewset(ModelViewSet):
    queryset = BusinessPaymentMethod.objects.all()
    serializer_class = BusinessPaymentMethodSerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions,
    ]

    def get_queryset(self):

        queryset = self.queryset

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_BUSINESS_PAYMENT_METHOD.value[0]
            + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_BUSINESS_PAYMENT_METHOD.value[0]
            + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()

        return queryset


class PaymentMethodViewset(ListModelMixin, GenericViewSet):
    queryset = PaymentMethod.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer
