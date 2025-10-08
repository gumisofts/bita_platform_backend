import uuid

from django.db import models

from core.models import BaseModel


class PaymentMethod(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to="payment_methods/", null=True, blank=True)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255)


class Transaction(BaseModel):
    class TransactionType(models.TextChoices):
        SALE = "SALE", "Sale"
        EXPENSE = "EXPENSE", "Expense"
        DEBT = "DEBT", "Debt"
        REFUND = "REFUND", "Refund"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order",
        related_name="transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "business.Branch", related_name="transactions", on_delete=models.CASCADE
    )
    business = models.ForeignKey(
        "business.Business",
        related_name="transactions",
        on_delete=models.CASCADE,
    )
    payment_method = models.ForeignKey(
        "finances.BusinessPaymentMethod",
        related_name="transactions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    total_paid_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Transaction {self.id} - {self.type} ({self.total_paid_amount})"


class BusinessPaymentMethod(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)

    business = models.ForeignKey(
        "business.Business",
        related_name="payment_methods",
        on_delete=models.CASCADE,
    )
    branch = models.ForeignKey(
        "business.Branch",
        related_name="payment_methods",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    label = models.CharField(max_length=255)

    identifier = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.label} - {self.business.name}"
