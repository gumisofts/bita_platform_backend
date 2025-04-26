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
    customer_id = models.UUIDField()
    employee_id = models.UUIDField()
    total_payable = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PROCESSING
    )

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class OrderItem(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    item = models.ForeignKey(
        "inventories.Item",
        on_delete=models.CASCADE,
    )
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"Item {self.item_id} in Order {self.order.id}"
