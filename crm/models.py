from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models

from accounts.models import Business


class Customer(models.Model):
    email = models.EmailField(unique=True)
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
    full_name = models.CharField(max_length=255)
    business = models.ForeignKey(Business, on_delete=models.CASCADE)


class GiftCard(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True
    )
    redeemed = models.BooleanField(default=False)
    redeemed_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField()
