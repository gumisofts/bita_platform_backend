from django.db import transaction as db_transaction
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Order, OrderItem, Transaction
from .serializers import OrderItemSerializer, OrderSerializer, TransactionSerializer


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


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    http_method_names = ["get", "post"]
