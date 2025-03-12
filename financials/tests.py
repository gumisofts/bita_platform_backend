import uuid

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Order, Transaction


class OrderAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.order = Order.objects.create(
            customer_id=uuid.uuid4(),
            employee_id=uuid.uuid4(),
            status=Order.StatusChoices.PROCESSING,
        )

    def test_create_order(self):
        response = self.client.post(
            "/financial/orders/",
            {
                "customer_id": str(uuid.uuid4()),
                "employee_id": str(uuid.uuid4()),
                "status": Order.StatusChoices.PROCESSING,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 2)

    def test_update_order_status_without_payment_method(self):
        response = self.client.patch(
            f"/financial/orders/{self.order.id}/",
            {"status": Order.StatusChoices.COMPLETED},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_update_order_status_with_valid_payment_method(self):
        response = self.client.patch(
            f"/financial/orders/{self.order.id}/",
            {
                "status": Order.StatusChoices.COMPLETED,
                "payment_method": Transaction.PaymentMethod.CASH,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.StatusChoices.COMPLETED)
        self.assertEqual(Transaction.objects.count(), 1)


class TransactionAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.order = Order.objects.create(
            customer_id=uuid.uuid4(),
            employee_id=uuid.uuid4(),
            status=Order.StatusChoices.PROCESSING,
        )
        self.transaction_data = {
            "order": self.order.id,
            "type": Transaction.TransactionType.SALE,
            "total_paid_amount": "100.00",
            "total_left_amount": "0.00",
            "payment_method": Transaction.PaymentMethod.CASH,
        }

    def test_create_transaction(self):
        response = self.client.post("/financial/transactions/", self.transaction_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Transaction.objects.count(), 1)
