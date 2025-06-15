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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["first_name"]

    @staticmethod
    def normalize_phone(phone_number):
        return phone_number

    def __str__(self):
        return f"User({str(self.id)})"


class PhoneChangeRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
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
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()


class EmailChangeRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    new_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
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

    def save(self, force_insert=False, *args, **kwargs):
        print(kwargs)
        print(args)
        if force_insert:
            self.code = make_password(self.code)
        return super().save(force_insert=force_insert, *args, **kwargs)


class UserDevice(BaseModel):
    fcm_token = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
