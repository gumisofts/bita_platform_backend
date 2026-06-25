from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from core.models import BaseModel


class Waitlist(BaseModel):
    """A prospective user who signed up before/while the marketplace launches."""

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    business_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        db_table = "market_waitlist"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class Review(BaseModel):
    """A rating + text review targeting exactly one of a Business or an ItemVariant."""

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="market_reviews",
    )
    reviewer_name = models.CharField(max_length=255, blank=True)
    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reviews",
    )
    variant = models.ForeignKey(
        "inventories.ItemVariant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reviews",
    )

    class Meta:
        db_table = "market_review"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(business__isnull=False) & Q(variant__isnull=True))
                    | (Q(business__isnull=True) & Q(variant__isnull=False))
                ),
                name="market_review_exactly_one_target",
            )
        ]

    def __str__(self):
        target = self.business_id or self.variant_id
        return f"{self.rating}★ by {self.reviewer_name or 'anonymous'} ({target})"


class MarketplaceOrder(BaseModel):
    """A buyer's order inquiry sent to a supplier. Records intent only — stock is
    not changed; the supplier follows up to fulfil it."""

    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="marketplace_orders",
    )
    buyer_name = models.CharField(max_length=255)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=32, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="PENDING")
    total_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "market_order"
        ordering = ["-created_at"]

    def __str__(self):
        return f"MarketplaceOrder {self.id} ({self.status})"


class MarketplaceOrderItem(BaseModel):
    order = models.ForeignKey(
        MarketplaceOrder, on_delete=models.CASCADE, related_name="items"
    )
    variant = models.ForeignKey(
        "inventories.ItemVariant",
        on_delete=models.CASCADE,
        related_name="marketplace_order_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "market_order_item"

    def __str__(self):
        return f"{self.quantity} x {self.variant_id}"


class VariantImage(BaseModel):
    """Optional image attached directly to an ItemVariant. When present these take
    precedence over the parent Item's images for that variant."""

    variant = models.ForeignKey(
        "inventories.ItemVariant", on_delete=models.CASCADE, related_name="images"
    )
    file = models.ForeignKey("files.FileMeta", on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)
    is_thumbnail = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "market_variant_image"
        ordering = ["-is_primary", "created_at"]

    def __str__(self):
        return f"image for variant {self.variant_id}"
