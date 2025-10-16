from uuid import uuid4

from django.db import models

from core.models import BaseModel

# Create your models here.
# Define Order status


class Order(BaseModel):
    class StatusChoices(models.TextChoices):
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"

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
