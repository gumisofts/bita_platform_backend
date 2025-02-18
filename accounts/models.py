from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from .manager import CustomUserManager
from django.conf import settings
import uuid


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class User(TimeStampedModel, AbstractUser):
    username = None
    email = models.EmailField(unique=True, blank=True)  # Overriden to make it unique
    phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^(9|7)\d{8}$",
                message="Phone number must be entered in the format: '912345678 / 712345678'. Up to 9 digits allowed.",
            )
        ],
        unique=True,
        blank=True,
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name"]

    def __str__(self):
        return self.email


class Business(TimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="businesses",
    )
    name = models.CharField(max_length=255)
    address = models.TextField()
    category = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=255)
    phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^(9|7)\d{8}$",
                message="Phone number must be entered in the format: '912345678 / 712345678'. Up to 9 digits allowed.",
            )
        ],
    )
    email = models.EmailField()
    address = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="suppliers",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="suppliers",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name


class Customer(TimeStampedModel):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^(9|7)\d{8}$",
                message="Phone number must be entered in the format: '912345678 / 712345678'. Up to 9 digits allowed.",
            )
        ],
    )
    email = models.EmailField()
    address = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customers",
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="customers",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Employee(User):
    ROLE_CHOICES = [
        ("Manager", "Manager"),
        ("Sales", "Sales"),
        ("Admin", "Admin"),
    ]
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_employees",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.email} - {self.role}"


class EmployeeInvitation(TimeStampedModel):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=10, choices=Employee.ROLE_CHOICES)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_invitations",
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="employee_invitations",
    )
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitation for {self.email} - Accepted: {self.accepted}"


class EmployeeBusiness(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Employee.ROLE_CHOICES)
