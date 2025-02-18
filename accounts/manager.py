from django.contrib.auth.models import BaseUserManager
import re
from django.core.exceptions import ValidationError


def validate_phone(phone):
    phone_regex = r"^(9|7)\d{8}$"
    if not re.match(phone_regex, phone):
        raise ValidationError(
            "Phone number must be entered in the format: '912345678 / 712345678'. Up to 9 digits allowed."
        )


class CustomUserManager(BaseUserManager):
    def create_user(self, email, phone, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError("The Email field must be set")
        if not phone:
            raise ValueError("The Phone field must be set")
        validate_phone(phone)
        email = self.normalize_email(email)
        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, phone, password, **extra_fields)
