from uuid import uuid4

from django.contrib.auth.models import AbstractUser, Permission
from django.core.validators import RegexValidator
from django.db import models

from .manager import CustomUserManager


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True, blank=True, null=True)
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
        return self.email or self.username or str(self.id)


class Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    lat = models.FloatField()
    lng = models.FloatField()
    plus_code = models.IntegerField(null=True, blank=True)
    sublocality = models.CharField(max_length=255, null=True)
    locality = models.CharField(max_length=255, null=True)
    admin_2 = models.CharField(max_length=255, null=True)
    admin_1 = models.CharField(max_length=255)
    country = models.CharField(max_length=255)

    def __str__(self):
        return f"""
        {self.sublocality}, {self.locality}, {self.admin_1}, {self.country}
        """


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Business(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    business_type_choices = [
        ("retail", "Retail"),
        ("whole_sale", "Wholesale"),
        ("manufacturing", "Manufacturing"),
        ("service", "Service"),
    ]
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="businesses",
        null=True,
    )
    business_type = models.CharField(choices=business_type_choices, max_length=255)
    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
    )
    category = models.ManyToManyField(
        Category,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Files and Images

    def __str__(self):
        return self.name


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    role_name = models.CharField(max_length=255)
    role_code = models.IntegerField()


# class Permission(Permission):
#     id = models.UUIDField(primary_key=True, default=uuid4, editable=False)


class RolePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    permission = models.ForeignKey(
        Permission,
        on_delete=models.SET_NULL,
        null=True,
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
    )


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.SET_NULL,
        null=True,
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return f"{self.user.email} - {self.role} at {self.business}"


class BusinessActivity(models.Model):
    MODEL_CHOICES = [
        (1, "User"),
        (2, "Address"),
        (3, "Password"),
        (4, "Business"),
        (5, "BusinessActivity"),
        (6, "PhoneChangeRequest"),
        (7, "EmailChangeRequest"),
        (8, "Employee"),
        (9, "Branch"),
        (10, "Role"),
        (11, "RolePermission"),
        (12, "Category"),
    ]
    ACTION_CHOICES = [
        (1, "Create"),
        (2, "Update"),
        (3, "Delete"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    model = models.IntegerField(choices=MODEL_CHOICES)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.SET_NULL,
        null=True,
    )
    action = models.IntegerField(choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)


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


class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    business = models.ForeignKey(
        Business,
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Password(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="user_passwords",
    )
    password = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
