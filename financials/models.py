import uuid

from django.db import models

from inventory.models import Item


class Order(models.Model):
    class StatusChoices(models.TextChoices):
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_id = models.UUIDField()
    employee_id = models.UUIDField()
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PROCESSING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
    )
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"Item {self.item_id} in Order {self.order.id}"


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        SALE = "SALE", "Sale"
        EXPENSE = "EXPENSE", "Expense"
        DEBT = "DEBT", "Debt"
        REFUND = "REFUND", "Refund"

    class PaymentMethod(models.TextChoices):
        CBE = "CBE", "Commercial Bank of Ethiopia"
        AWASH = "AWASH", "Awash Bank"
        TELEBIRR = "TELEBIRR", "Tele-Birr"
        CASH = "CASH", "Cash"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        related_name="transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    total_paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_left_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.id} - {self.type} ({self.amount})"
