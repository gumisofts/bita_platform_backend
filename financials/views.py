from django.db import transaction as db_transaction
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from inventories.models import SuppliedItem

from .models import BusinessPaymentMethod, Order, OrderItem, Transaction
from .serializers import (
    BusinessPaymentMethodSerializer,
    OrderItemSerializer,
    OrderSerializer,
    TransactionSerializer,
)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    http_method_names = ["get", "post", "patch"]

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


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    http_method_names = ["post"]

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


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    http_method_names = ["get", "post"]


# CRUD for Business Payment Methods
class BusinessPaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = BusinessPaymentMethod.objects.all()
    serializer_class = BusinessPaymentMethodSerializer

    def get_queryset(self):
        business_id = self.request.query_params.get("business_id")
        if business_id:
            return self.queryset.filter(business_id=business_id)
        return self.queryset


@api_view(["GET"])
def get_business_payment_methods(request, business_id):
    # Fetch system-wide default payment methods
    default_methods = [
        {"id": None, "name": value} for key, value in Transaction.PaymentMethod.choices
    ]

    # Fetch custom payment methods for the business
    custom_methods = BusinessPaymentMethod.objects.filter(
        business_id=business_id
    ).values("id", "name")

    all_methods = list(default_methods) + list(custom_methods)

    return Response(all_methods)
