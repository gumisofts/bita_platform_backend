from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator, EmailValidator
from django.db import models

from accounts.models import Business
from financials.models import Order


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
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),

    ]
    code = models.UUIDField(default=uuid4, editable=False, unique=True)
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="gift_cards"
    )
    original_value = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    remaining_value = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='active')
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Gift card ({self.code}) ({self.customer})"


class GiftCardTransaction(models.Model):
    gift_card = models.ForeignKey(
        GiftCard, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transaction of {self.amount} for {self.gift_card}"


# class GiftCard(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
#     GIFT_CARD_TYPE_CHOICES = [
#         (1, "Specific Item"),
#         (2, "Business Item"),
#         (3, "Platform Item"),
#     ]

#     business = models.ForeignKey(Business, on_delete=models.CASCADE)
#     owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
#     created_by = models.ForeignKey(
#         get_user_model(),
#         on_delete=models.SET_NULL,
#         null=True,
#         related_name="created_giftcards",
#     )
#     redeemed = models.BooleanField(default=False)
#     redeemed_at = models.DateTimeField(null=True)
#     expires_at = models.DateTimeField()
#     type = models.IntegerField(choices=GIFT_CARD_TYPE_CHOICES)
