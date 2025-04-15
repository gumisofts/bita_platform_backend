from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator, MinValueValidator, RegexValidator
from django.db import models

from accounts.models import Business
from financials.models import Order

User = get_user_model()


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    full_name = models.CharField(max_length=255)
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
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

    def __str__(self):
        return self.full_name


class GiftCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    GIFT_CARD_TYPE_CHOICES = [
        (1, "Specific Item"),
        (2, "Business Item"),
        (3, "Platform Item"),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_giftcards",
    )
    redeemed = models.BooleanField(default=False)
    redeemed_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField()
    type = models.IntegerField(choices=GIFT_CARD_TYPE_CHOICES)
