from django.db import transaction as db_transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from business.permissions import (
    AdditionalBusinessPermissionNames,
    BranchLevelPermission,
    BusinessLevelPermission,
    GuardianObjectPermissions,
)
from core.utils import is_valid_uuid
from finances.models import Transaction
from inventories.models import SuppliedItem
from orders.models import Order, OrderItem
from orders.serializers import OrderItemSerializer, OrderListSerializer, OrderSerializer


class OrderItemViewset(ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    http_method_names = ["post"]
    permission_classes = [
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions
    ]

    def create(self, request, *args, **kwargs):
        with db_transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Save the new OrderItem
            order_item = serializer.save()
            # Get the associated Order
            order = order_item.order

            # Get the latest supply price of the item
            latest_supply = (
                SuppliedItem.objects.filter(item=order_item.item)
                .order_by("-timestamp")
                .first()
            )

            if latest_supply:
                item_unit_price = latest_supply.price
            else:
                return Response(
                    {"error": "No supply record found for this item."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the order's total_payable field
            order.total_payable += item_unit_price * order_item.quantity
            order.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderViewset(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    http_method_names = ["get", "post", "patch"]
    permission_classes = [
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            OrderListSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.business:
            raise ValidationError({"detail": "Empty or invalid business"})

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ORDER.value[0] + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ORDER.value[0] + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        if self.action == "retrieve":
            return OrderListSerializer
        return self.serializer_class

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        previous_status = order.status

        response = super().update(request, *args, **kwargs)

        try:
            new_status = response.data.get("status")

            payment_method = request.data.get("payment_method")

            # If the status is changing to COMPLETED or PARTIALLY_PAID, ensure payment method is provided
            if new_status in [
                Order.StatusChoices.COMPLETED,
                Order.StatusChoices.PARTIALLY_PAID,
            ]:
                if not payment_method:
                    return Response(
                        {
                            "error": "Payment method is required when completing or partially paying an order."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Validate payment method against allowed choices
                if payment_method not in dict(Transaction.PaymentMethod.choices):
                    return Response(
                        {"error": "Invalid payment method."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Create a transaction if the status changed
                if previous_status != new_status:
                    with db_transaction.atomic():
                        transaction = Transaction.objects.create(
                            order=order,
                            type=Transaction.TransactionType.SALE,
                            # left 0 for lack of price value in inventory.Item object
                            total_paid_amount=0,
                            total_left_amount=0,
                            payment_method=payment_method,
                        )
                        transaction.save()

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return response

    @action(detail=True, methods=["get"])
    def checkout(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status == Order.StatusChoices.COMPLETED:
            return Response(
                {"error": "Order is already completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = Order.StatusChoices.COMPLETED
        order.save()
        return Response(OrderListSerializer(order).data, status=status.HTTP_200_OK)
