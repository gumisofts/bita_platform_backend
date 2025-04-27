from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.validators import RegexValidator
from django.db import models

from core.models import BaseModel

User = get_user_model()


class Address(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    lat = models.FloatField()
    lng = models.FloatField()
    plus_code = models.CharField(null=True, blank=True)
    sublocality = models.CharField(max_length=255, null=True)
    locality = models.CharField(max_length=255, null=True)
    admin_2 = models.CharField(max_length=255, null=True)
    admin_1 = models.CharField(max_length=255)
    country = models.CharField(max_length=255)

    def __str__(self):
        return f"""
        {self.admin_1}, {self.country}:-({self.lat}, {self.lng})
        """


class Industry(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    image = models.ForeignKey(
        "files.FileMeta", null=True, blank=True, on_delete=models.SET_NULL
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Category(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, null=True)
    is_active = models.BooleanField(default=True)
    image = models.ForeignKey(
        "files.FileMeta", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.name


class Business(BaseModel):
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
    categories = models.ManyToManyField(Category, related_name="businesses")
    background_image = models.ForeignKey(
        "files.FileMeta", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.name


class Role(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    role_name = models.CharField(max_length=255)
    # role_code = models.IntegerField()
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        null=True,
        related_name="roles",
    )

    def __str__(self):
        return f"{self.role_name} - {self.business.name}"


class Employee(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        null=True,
        related_name="employees",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        related_name="employees",
    )
    branch = models.ForeignKey(
        "Branch",
        on_delete=models.SET_NULL,
        null=True,
        related_name="employees",
    )

    def __str__(self):
        return f"{self.user.email} - {self.role} at {self.business}"


class BusinessActivity(BaseModel):
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


class BusinessImage(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    business = models.OneToOneField(
        Business, on_delete=models.CASCADE, related_name="business_images"
    )
    image = models.ManyToManyField(
        "files.FileMeta", blank=True, related_name="business_images"
    )

    class Meta:
        ordering = ["created_at", "updated_at"]


class Branch(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.ForeignKey(
        Address,
        on_delete=models.CASCADE,
        null=True,
        related_name="branches",
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        null=True,
        related_name="branches",
    )

    def __str__(self):
        return f"{self.name} - {self.business.name}"
