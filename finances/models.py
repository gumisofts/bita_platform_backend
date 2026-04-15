import uuid

from django.db import models
from django.db.models import Q

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
    category = models.CharField(max_length=100, null=True, blank=True)
    total_paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_left_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )

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
    label = models.CharField(max_length=255, null=True, blank=True)
    identifier = models.CharField(max_length=255, unique=True, null=True, blank=True)

    def _same_scope_filter(self):
        """Filter for same business + branch scope (for counter)."""
        scope = Q(business=self.business, payment=self.payment)
        if self.branch_id is not None:
            scope &= Q(branch=self.branch)
        else:
            scope &= Q(branch__isnull=True)
        return scope

    def save(self, *args, **kwargs):
        if not self.label and self.payment_id:
            # Use payment method name + counter (same business/branch/payment type)
            scope = self._same_scope_filter()
            existing = (
                BusinessPaymentMethod.objects.filter(scope).exclude(pk=self.pk).count()
            )
            self.label = f"{self.payment.name} {existing + 1}"
        if not self.identifier:
            self.identifier = str(uuid.uuid4())
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        """Display name: label if set, else payment name + counter (for unsaved)."""
        if self.label:
            return self.label
        if self.payment_id:
            return self.payment.name
        return ""

    def __str__(self):
        return f"{self.display_name or 'Unnamed'} - {self.business.name}"
