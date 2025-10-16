import re

from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError


def validate_phone(phone):
    phone_regex = r"^(9|7)\d{8}$"
    if not re.match(phone_regex, phone):
        raise ValidationError(
            "Phone number must be entered in the format: \
            '912345678 / 712345678'. Up to 9 digits allowed."
        )


class CustomUserManager(BaseUserManager):
    def create(self, **kwargs):
        return self.create_user(**kwargs)

    def create_user(
        self,
        email=None,
        phone_number=None,
        password=None,
        **extra_fields,
    ):
        """Create and return a regular user."""
        if phone_number:
            validate_phone(phone_number)
        if email:
            email = self.normalize_email(email)
        user = self.model(
            email=email,
            phone_number=phone_number,
            **extra_fields,
        )
        if password:
            user.set_password(password)
        user.save()
        return user

    def create_superuser(
        self,
        email=None,
        phone_number=None,
        password=None,
        **extra_fields,
    ):
        """Create and return a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_phone_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, phone_number, password, **extra_fields)
