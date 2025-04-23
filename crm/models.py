from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator, RegexValidator
from django.db import models

from accounts.models import Business

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
    STATUS_CHOICES = [
        ("new", "New"),
        ("active", "Active"),
        ("issued", "issued"),
        ("redeemed", "redeemed"),
        ("expired", "Expired"),
    ]
    CARD_TYPE = [
        ('platform', 'Platform'),
        ('business', 'Business'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.IntegerField()
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_giftcards")
    issued_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="issued_giftcards")

    products = models.ManyToManyField('inventories.Item', blank=True)

    current_owner = models.ForeignKey(
        "Customer", on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name="owned_giftcards"
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="active")
    card_type = models.CharField(
        max_length=30, choices=CARD_TYPE, default='business')

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Gift card ({self.code}) ({self.customer})"


class GiftCardTransfer(models.Model):
    gift_card = models.ForeignKey(
        GiftCard, related_name='gift_cards', on_delete=models.CASCADE)
    from_customer = models.ForeignKey(
        Customer, related_name='gift_card_transfer',
        on_delete=models.SET_NULL, null=True)
    to_customer = models.ForeignKey(
        Customer, related_name='gift_card_receiver',
        on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
