from uuid import uuid4

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from core.models import BaseModel
from files.models import FileMeta


class Property(BaseModel):
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    item_variant = models.ForeignKey(
        "ItemVariant", on_delete=models.CASCADE, related_name="properties"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Property"
        verbose_name_plural = "Properties"


class Group(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    business = models.ForeignKey(
        "business.Business", on_delete=models.CASCADE, related_name="groups"
    )

    class Meta:
        db_table = "group"
        get_latest_by = "created_at"
        ordering = ["created_at", "updated_at"]

    def __str__(self):
        return self.name


class Item(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="items", null=True, blank=True
    )  # TODO change it to m2m
    min_selling_quota = models.PositiveBigIntegerField(default=1)
    categories = models.ManyToManyField(
        "business.Category", blank=True, related_name="items"
    )
    inventory_unit = models.CharField(max_length=255)
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE)
    branch = models.ForeignKey("business.Branch", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    notify_below = models.PositiveIntegerField(default=1)
    receive_online_orders = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_returnable = models.BooleanField(default=False)
    is_visible_online = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ItemVariant(BaseModel):
    item = models.ForeignKey(Item, related_name="variants", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(1)],
        null=True,
        blank=True,
    )
    quantity = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=255, unique=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class ItemImage(BaseModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    file = models.ForeignKey(FileMeta, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_primary = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    is_thumbnail = models.BooleanField(default=False)

    def __str__(self):
        return self.item.name


class Supplier(BaseModel):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^(9|7)\d{8}$",
                message="Phone number must be entered in the format: \
                    '912345678 / 712345678'. Up to 9 digits allowed.",
            )
        ],
        unique=True,
        blank=True,
    )
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Supply(BaseModel):
    label = models.CharField(max_length=255)
    branch = models.ForeignKey("business.Branch", on_delete=models.CASCADE)
    business = models.ForeignKey(
        "business.Business", on_delete=models.CASCADE, null=True, blank=True
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="supplies",
        null=True,
        blank=True,
    )
    payment_method = models.ForeignKey(
        "finances.PaymentMethod",
        on_delete=models.CASCADE,
        related_name="supplies",
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ("label", "branch")
        verbose_name = "Supply"
        verbose_name_plural = "Supplies"

    def __str__(self):
        return self.label


class SuppliedItem(BaseModel):
    quantity = models.PositiveIntegerField()
    initial_quantity = models.PositiveIntegerField(default=0)
    item = models.ForeignKey(
        Item,
        related_name="supplied_items",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    variant = models.ForeignKey(
        ItemVariant, related_name="supplied_items", on_delete=models.CASCADE
    )
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    is_returnable = models.BooleanField(default=False)
    is_visible_online = models.BooleanField(default=True)
    notify_below = models.PositiveIntegerField(default=1)
    batch_number = models.CharField(max_length=255)
    product_number = models.CharField(max_length=255)
    expire_date = models.DateField(null=True, blank=True)
    man_date = models.DateField(null=True, blank=True)
    supply = models.ForeignKey(
        Supply, on_delete=models.CASCADE, related_name="supplied_items"
    )
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.item} - {self.quantity}"


class Pricing(BaseModel):
    price = models.PositiveBigIntegerField()
    item_variant = models.ForeignKey(
        ItemVariant, on_delete=models.CASCADE, related_name="pricings"
    )
    min_selling_quota = models.PositiveBigIntegerField()


class ReturnRecall(BaseModel):
    item_variant = models.ForeignKey(ItemVariant, on_delete=models.CASCADE)
    remarks = models.TextField(blank=True)
    quantity = models.PositiveIntegerField()


class InventoryMovement(BaseModel):
    """Model to track inventory movements between branches"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("shipped", "Shipped"),
        ("received", "Received"),
        ("cancelled", "Cancelled"),
    ]

    movement_number = models.CharField(max_length=50, unique=True)
    from_branch = models.ForeignKey(
        "business.Branch", on_delete=models.CASCADE, related_name="outgoing_movements"
    )
    to_branch = models.ForeignKey(
        "business.Branch", on_delete=models.CASCADE, related_name="incoming_movements"
    )
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="requested_movements",
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_movements",
    )
    shipped_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipped_movements",
    )
    received_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_movements",
    )
    notes = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.movement_number}: {self.from_branch} → {self.to_branch}"

    def save(self, *args, **kwargs):
        if not self.movement_number:
            # Generate movement number (format: MOV-YYYYMMDD-XXXX)
            import random

            from django.utils import timezone

            date_str = timezone.now().strftime("%Y%m%d")
            random_num = str(random.randint(1000, 9999))
            self.movement_number = f"MOV-{date_str}-{random_num}"
        super().save(*args, **kwargs)


class InventoryMovementItem(BaseModel):
    """Items included in an inventory movement"""

    movement = models.ForeignKey(
        InventoryMovement, on_delete=models.CASCADE, related_name="movement_items"
    )
    variant = models.ForeignKey(ItemVariant, on_delete=models.CASCADE)
    supplied_item = models.ForeignKey(SuppliedItem, on_delete=models.CASCADE)
    quantity_requested = models.PositiveIntegerField()
    quantity_shipped = models.PositiveIntegerField(default=0)
    quantity_received = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("movement", "supplied_item")

    def __str__(self):
        return f"{self.supplied_item.item.name} - {self.quantity_requested} units"
