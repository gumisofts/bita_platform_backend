from django.db import models
from django.core.validators import MinValueValidator
import enum
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
import requests


# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "category"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Location(models.Model):
    lat = models.DecimalField(null=True, max_digits=12, decimal_places=10)
    lng = models.DecimalField(null=True, max_digits=13, decimal_places=10)
    region = models.CharField(null=True, max_length=255)
    zone = models.CharField(null=True, max_length=255)
    woreda = models.CharField(null=True, max_length=255)
    kebele = models.CharField(null=True, max_length=255)
    city = models.CharField(null=True, max_length=255)
    sub_city = models.CharField(null=True, max_length=255)

    class Meta:
        db_table = "location"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return f"{self.city} {self.sub_city}"


class Store(models.Model):
    business_id = models.IntegerField()
    name = models.CharField(max_length=255)
    location = models.OneToOneField(
        Location, on_delete=models.CASCADE, related_name="locations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "store"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Manufacturer(models.Model):
    name = models.CharField(max_length=255)
    logo_url = models.URLField(blank=True, null=True)
    manufacturer_type = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "manfacturer"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="items"
    )
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True)
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    is_returnable = models.BooleanField(default=True)
    notify_below = models.IntegerField()
    isvisible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "item"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.name


class ItemImage(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="item_images")
    image_id = models.IntegerField()

    class Meta:
        db_table = "item_image"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.image_id


class ReturnRecall(models.Model):
    PENDING = "P"
    APPROVED = "A"
    REJECTED = "R"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=PENDING)
    item = models.ForeignKey(
        Item, models.SET_NULL, null=True, blank=True, related_name="items"
    )
    reason = models.TextField(null=True, blank=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"ReturnRecall ({self.status}) - {self.quantity} items"


class Supply(models.Model):
    units = [
        _("Piece (pc)"),
        _("Kilogram(kg)"),
        _("Gram(g)"),
        _("Pound(lb)"),
        _("Ounce(oz)"),
        _("Liter(L)"),
        _("Milliliter(mL)"),
        _("Fluid Ounce (fl oz)"),
        _("Gallon(gal)"),
        _("Meter (m)"),
        _("Centimeter (cm)"),
        _("Inch (in)"),
        _("Foot (ft)"),
        _("Square Meter"),
        _("Square Foot"),
        _("Cubic Meter"),
        _("Cubic Foot"),
        _("Dozen (dz)"),
        _("Pack (pk)"),
        _("Set (set)"),
    ]

    item = models.ForeignKey(
        Item, models.CASCADE, related_name="item_supply", default=1
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    sale_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    cost_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(1)]
    )
    unit = models.CharField(max_length=255, choices=map(lambda x: (x, x), units))
    expiration_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=255, unique=True)
    man_date = models.DateField(null=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="stores")
    supplier_id = models.IntegerField()

    class Meta:
        db_table = "supply"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return self.item.name


class StockMovement(models.Model):
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True)
    from_store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        related_name="outgoing_movements",
        null=True,
        blank=True,
    )
    to_store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        related_name="incoming_movements",
        null=True,
        blank=True,
    )
    quantity = models.PositiveIntegerField()
    reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        db_table = "stockmovement"
        get_latest_by = "id"
        ordering = ["id"]

    def __str__(self):
        return f"Movement {self.id}: {self.quantity} quantity of {self.supply.name} moved from {self.from_store.name} to {self.to_store.name}"


class SupplyReservation(models.Model):
    supply = models.ForeignKey(
        Supply, on_delete=models.CASCADE, related_name="reservations"
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reserved_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("cancelled", "Cancelled"),
            ("fulfilled", "Fulfilled"),
        ],
        default="active",
    )

    class Meta:
        db_table = "supply_reservation"
        ordering = ["-reserved_at"]

    def save(self, *args, **kwargs):
        # Check if updating an existing record and status has changed to fulfilled.
        if self.pk:
            previous = SupplyReservation.objects.get(pk=self.pk)
            if previous.status != "fulfilled" and self.status == "fulfilled":
                # Reduce supply quantity by this reservation's quantity.
                self.supply.quantity = self.supply.quantity - self.quantity
                self.supply.save()
        else:
            # For new records, if the reservation is created as fulfilled.
            if self.status == "fulfilled":
                self.supply.quantity = self.supply.quantity - self.quantity
                self.supply.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reservation for {self.supply} - {self.quantity}"
