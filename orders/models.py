from uuid import uuid4

from django.db import models

from core.models import BaseModel

# Create your models here.
# Define Order status


class Order(BaseModel):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        CONFIRMED = "CONFIRMED", "Confirmed"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        COMPLETED = "COMPLETED", "Completed"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        ON_HOLD = "ON_HOLD", "On Hold"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"
        RETURNED = "RETURNED", "Returned"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    customer = models.ForeignKey(
        "crms.Customer", on_delete=models.SET_NULL, null=True, blank=True
    )
    employee = models.ForeignKey(
        "business.Employee", on_delete=models.SET_NULL, null=True, blank=True
    )
    total_payable = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PROCESSING
    )
    payment_method = models.ForeignKey(
        "finances.BusinessPaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE)
    branch = models.ForeignKey("business.Branch", on_delete=models.CASCADE)

    additional_info = models.JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class OrderItem(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    variant = models.ForeignKey(
        "inventories.ItemVariant",
        on_delete=models.CASCADE,
        related_name="items",
    )
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"Item {self.variant_id} in Order {self.order.id}"


class OrderHistory(BaseModel):
    """
    Model to track all changes made to an order
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    field_name = models.CharField(
        max_length=100, help_text="Name of the field that was changed"
    )
    old_value = models.TextField(
        null=True, blank=True, help_text="Previous value of the field"
    )
    new_value = models.TextField(
        null=True, blank=True, help_text="New value of the field"
    )
    changed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_changes",
        help_text="User who made the change",
    )
    changed_by_employee = models.ForeignKey(
        "business.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_changes",
        help_text="Employee who made the change",
    )
    change_reason = models.TextField(
        null=True, blank=True, help_text="Optional reason for the change"
    )

    class Meta:
        db_table = "order_history"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
            models.Index(fields=["field_name"]),
        ]

    def __str__(self):
        return f"Order {self.order.id} - {self.field_name} changed at {self.created_at}"
