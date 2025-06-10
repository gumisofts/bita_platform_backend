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

    def __str__(self):
        return self.name


class ItemVariant(BaseModel):
    item = models.ForeignKey(Item, related_name="variants", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    batch_number = models.CharField(max_length=255)
    sku = models.CharField(max_length=255, unique=True)
    expire_date = models.DateField(null=True, blank=True)
    man_date = models.DateField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_returnable = models.BooleanField(default=False)
    is_visible_online = models.BooleanField(default=True)
    receive_online_orders = models.BooleanField(default=True)
    notify_below = models.PositiveBigIntegerField()

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

    class Meta:
        unique_together = ("label", "branch")

    def __str__(self):
        return self.label


class SuppliedItem(BaseModel):
    quantity = models.PositiveIntegerField()
    item = models.ForeignKey(
        Item, related_name="supplied_items", on_delete=models.CASCADE
    )
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    batch_number = models.CharField(max_length=255)
    product_number = models.CharField(max_length=255, unique=True)
    expire_date = models.DateField(null=True, blank=True)
    man_date = models.DateField(null=True, blank=True)
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    supply = models.ForeignKey(
        Supply, on_delete=models.CASCADE, related_name="supplied_items"
    )

    def __str__(self):
        return self.item.name


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
