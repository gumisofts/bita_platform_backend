from uuid import uuid4

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from accounts.models import Branch, Business, Category
from files.models import FileMeta


class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    min_selling_quota = models.PositiveBigIntegerField(default=1)
    categories = models.ManyToManyField(Category, blank=True, related_name="items")
    inventory_unit = models.CharField(max_length=255)
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    notify_below = models.PositiveBigIntegerField()
    is_returnable = models.BooleanField(default=False)
    is_visible_online = models.BooleanField(default=True)
    receive_online_orders = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "item"
        get_latest_by = "created_at"
        ordering = ["created_at", "updated_at"]

    def __str__(self):
        return self.name


class ItemImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    item = models.OneToOneField(Item, on_delete=models.CASCADE)
    file = models.OneToOneField(FileMeta, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "item_image"
        get_latest_by = "created_at"
        ordering = ["created_at"]

    def __str__(self):
        return self.item.name


class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
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
    business = models.ForeignKey(Business, on_delete=models.CASCADE)

    class Meta:
        db_table = "supplier"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Supply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    supply_date = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    recipt = models.OneToOneField(
        FileMeta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "supply"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.name


class SuppliedItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    quantity = models.PositiveIntegerField()
    item = models.ManyToManyField(Item, related_name="supplied_items")
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    batch_number = models.CharField(max_length=255)
    expiry_date = models.DateTimeField()
    man_date = models.DateTimeField()
    barcode = models.CharField(max_length=255, unique=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    timestamp = models.DateField(auto_now_add=True)
    discount = models.PositiveIntegerField()
    supply = models.ManyToManyField(Supply)

    class Meta:
        db_table = "supplied_item"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.item.name


class Pricing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    price = models.PositiveBigIntegerField()
    min_quantity = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pricing"
        get_latest_by = "created_at"
        ordering = ["created_at"]
