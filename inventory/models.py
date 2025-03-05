import enum
import uuid

import requests
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext as _




class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    selling_quota = models.PositiveBigIntegerField()
    category =models.IntegerField()
    inventory_unit = models.CharField(max_length=255)
    business =  models.IntegerField()
    notify_below = models.PositiveBigIntegerField()
    is_returnable = models.BooleanField()
    make_online_available = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "item"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.name


class ItemImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item =  models.IntegerField()
    file =  models.IntegerField()

    class Meta:
        db_table = "item_image"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.item.name


class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    business =  models.IntegerField()

    class Meta:
        db_table = "supplier"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Supply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    supply_date = models.DateTimeField(auto_now_add=True)
    branch =  models.IntegerField()
    recipt =  models.IntegerField()

    class Meta:
        db_table = "supply"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.name


class SuppliedItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quantity = models.PositiveIntegerField()
    item =  models.IntegerField()
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
    business =  models.IntegerField()
    timestamp = models.DateField(auto_now_add=True)
    discount = models.PositiveIntegerField()
    supply = models.ManyToManyField(Supply)

    class Meta:
        db_table = "supplied_item"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.item.name
