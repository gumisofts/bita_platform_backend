import enum
import uuid

from django.db import models
from django.db.models import Q

from core.models import BaseModel


class AvailableVerifier(enum.Enum):
    CBE = "CBE", "Commercial Bank of Ethiopia"
    TELEBIRR = "TELEBIRR", "Telebirr"
    BOA = "BOA", "Bank of Abyssinia"
    CBEBIRR = "CBEBIRR", "CBE Birr"


class PaymentMethod(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to="payment_methods/", null=True, blank=True)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255)

    def get_or_create_cash_payment_method():
        id_uuid = uuid.UUID("00000000-0000-0000-0000-000000000001")
        payment_method, created = PaymentMethod.objects.get_or_create(
            name="CASH",
            defaults={
                "id": id_uuid,
                "short_name": "Cash",
            },
        )
        return payment_method

    def get_or_create_credit_payment_method():
        id_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        payment_method, created = PaymentMethod.objects.get_or_create(
            name="CREDIT",
            defaults={
                "id": id_uuid,
                "short_name": "Credit",
            },
        )
        return payment_method


class Transaction(BaseModel):
    class TransactionType(models.TextChoices):
        # Income types
        SALE = "SALE", "Sale"
        SERVICE_REVENUE = "SERVICE_REVENUE", "Service Revenue"
        OTHER_INCOME = "OTHER_INCOME", "Other Income"

        # Expense types
        EXPENSE = "EXPENSE", "Expense"
        RENT = "RENT", "Rent"
        SALARY = "SALARY", "Salary"
        UTILITY = "UTILITY", "Utility"
        PURCHASE = "PURCHASE", "Purchase"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        OTHER_EXPENSE = "OTHER_EXPENSE", "Other Expense"

        # Other
        DEBT = "DEBT", "Debt"
        REFUND = "REFUND", "Refund"

    # Canonical sets used for income/expense aggregations across reports.
    INCOME_TYPES = [
        TransactionType.SALE,
        TransactionType.SERVICE_REVENUE,
        TransactionType.OTHER_INCOME,
    ]
    EXPENSE_TYPES = [
        TransactionType.EXPENSE,
        TransactionType.RENT,
        TransactionType.SALARY,
        TransactionType.UTILITY,
        TransactionType.PURCHASE,
        TransactionType.MAINTENANCE,
        TransactionType.OTHER_EXPENSE,
        TransactionType.DEBT,
        TransactionType.REFUND,
    ]

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
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_transactions",
    )
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    total_paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, blank=True, null=True)

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
    receiver_name = models.CharField(max_length=255, null=True, blank=True)
    identifier = models.CharField(max_length=255, null=True, blank=True)

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

    class Meta:
        unique_together = ("business", "branch", "identifier")
