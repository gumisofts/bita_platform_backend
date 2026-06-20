from uuid import uuid4

from django.contrib.auth.hashers import (
    check_password,
    is_password_usable,
    make_password,
)
from django.contrib.auth.models import AbstractUser, Permission
from django.core.validators import RegexValidator
from django.db import models

from core.models import *

from .manager import CustomUserManager

regex_validator = RegexValidator(
    regex=r"^(9|7)\d{8}$",
    message="Phone number must be entered in the format: \
                    '912345678 / 712345678'. Up to 9 digits allowed.",
)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True, blank=True, null=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[regex_validator],
        unique=True,
        blank=True,
        null=True,
    )
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    telegram_id = models.BigIntegerField(
        null=True, blank=True, unique=True, db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["first_name"]

    @staticmethod
    def normalize_phone(phone_number):
        """Normalize a phone number to the bare local form stored in the DB.

        Phones are persisted in the ``^(9|7)\\d{8}$`` form (no country code),
        but external sources — notably Telegram contact sharing — return E.164
        (e.g. ``+251912345678`` / ``251912345678``). Strip the ``+``, spaces and
        separators, and a leading ``251`` country code so both forms compare
        equal. Unknown formats are returned digit-only and left to the caller.
        """
        if not phone_number:
            return phone_number
        digits = "".join(ch for ch in str(phone_number) if ch.isdigit())
        if digits.startswith("251") and len(digits) > 9:
            digits = digits[3:]
        return digits

    def __str__(self):
        representation = f"User({str(self.id)})"
        if self.email:
            representation = f"User({str(self.id)}, {self.email})"

        if self.phone_number:
            representation = f"User({str(self.id)}, {self.phone_number})"
        return representation


class PhoneChangeRequest(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    new_phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^(9|7)\d{8}$",
                message="Phone number must be entered in the format: \
                    '912345678 / 712345678'. Up to 9 digits allowed.",
            )
        ],
    )
    code = models.CharField(max_length=255)
    expires_at = models.DateTimeField()


class EmailChangeRequest(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    new_email = models.EmailField()
    code = models.CharField(max_length=255)
    expires_at = models.DateTimeField()


class TelegramLinkRequest(BaseModel):
    """A pending request to link a Telegram account to a Bita account by email.

    Created when a Mini App user (whose Telegram is not yet linked and whose
    shared phone matched no account) asks to connect to an existing account.
    A signed, single-use token is emailed; confirming it links ``telegram_id``
    to ``user``.
    """

    telegram_id = models.BigIntegerField(db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="telegram_link_requests",
    )
    email = models.EmailField()
    # Hashed token (make_password); the raw signed value is only ever emailed.
    token = models.CharField(max_length=255, db_index=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()


class Password(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="user_passwords",
    )
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def hash_password(password):
        return make_password(password)


class ResetPasswordRequest(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)


class VerificationCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    code = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="codes")
    phone_number = models.CharField(
        max_length=255, validators=[], null=True, blank=True
    )
    email = models.CharField(max_length=255, validators=[], null=True, blank=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Hash the code on first insert so it is never stored in plaintext.
        # `is_password_usable` returns False for empty/raw values, so we only
        # hash when the stored value isn't already a password hash. This makes
        # the call idempotent across QuerySet.create() and explicit save() calls.
        if self._state.adding and self.code and is_password_usable(self.code):
            self.code = make_password(self.code)
        return super().save(*args, **kwargs)


class UserDevice(BaseModel):
    fcm_token = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default="unknown")
    device_id = models.CharField(max_length=255, default="unknown")
    os = models.CharField(max_length=255, default="unknown")
    manufacturer = models.CharField(max_length=255, default="unknown")
    app_version = models.CharField(max_length=255, default="unknown")
    app_build_number = models.CharField(max_length=255, default="unknown")
    app_version_code = models.CharField(max_length=255, default="unknown")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return (
            f"{self.name} ({self.label}) — {'active' if self.is_active else 'disabled'}"
        )
