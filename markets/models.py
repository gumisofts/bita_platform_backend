from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import BaseModel


class Review(BaseModel):
    """Generic review/rating for both products (ItemVariant) and businesses."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")

    reviewer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("content_type", "object_id", "reviewer")

    def __str__(self):
        return f"{self.reviewer} — {self.rating}★ on {self.content_type.model} {self.object_id}"
