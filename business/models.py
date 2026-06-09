import enum
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from core.models import BaseModel

User = get_user_model()


# Models whose permissions live on the Business object itself.
# These are things that span the whole business rather than a single branch.
BUSINESS_SCOPED_MODELS: list[str] = [
    "branch",
    "employee",
    "address",
    "employeeinvitation",
    "group",
    "customer",
]

# Models whose permissions live on a Branch object.
# Owners / admins receive _branch perms on every branch instead of a single
# _business perm so that access stays consistent with manager/employee roles
# and new branches are handled automatically via the Branch post-save signal.
BRANCH_SCOPED_MODELS: list[str] = [
    "order",
    "item",
    "inventorymovement",
    "inventory",
    "property",
    "itemvariant",
    "supplier",
    "businesspaymentmethod",
    "transaction",
    "giftcard",
    "supply",
]

# Full list used only for generating Meta.permissions on Business and Branch.
PERMISSIONED_MODELS: list[str] = BUSINESS_SCOPED_MODELS + BRANCH_SCOPED_MODELS

CRUD_ACTIONS: list[str] = ["add", "change", "delete", "view"]

# Human-readable overrides for compound model names.
_MODEL_DISPLAY_NAMES: dict[str, str] = {
    "employeeinvitation": "employee invitation",
    "inventorymovement": "inventory movement",
    "itemvariant": "item variant",
    "businesspaymentmethod": "business payment method",
    "giftcard": "gift card",
}


def biz_perm(model_name: str, action: str, scope: str = "business") -> str:
    """Return the guardian permission codename for a business/branch-scoped action.

    Example: biz_perm("item", "view", "branch") → "can_view_item_branch"
    """
    return f"can_{action}_{model_name}_{scope}"


def _generate_permissions(scope: str, models: list[str]) -> list[tuple[str, str]]:
    """Generate the Meta.permissions list for a given scope and model list."""
    return [
        (
            biz_perm(model, action, scope),
            f"Can {action} {_MODEL_DISPLAY_NAMES.get(model, model)}",
        )
        for model in models
        for action in CRUD_ACTIONS
    ]


class Address(BaseModel):
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
    name = models.CharField(max_length=255)
    image = models.ForeignKey(
        "files.FileMeta", null=True, blank=True, on_delete=models.SET_NULL
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Category(BaseModel):
    name = models.CharField(max_length=255)
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, null=True)
    is_active = models.BooleanField(default=True)
    image = models.ForeignKey(
        "files.FileMeta", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.name


class Business(BaseModel):
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
    address = models.OneToOneField(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business",
    )
    categories = models.ManyToManyField(Category, related_name="businesses")
    background_image = models.ForeignKey(
        "files.FileMeta", on_delete=models.SET_NULL, null=True, blank=True
    )
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        permissions = _generate_permissions("business", BUSINESS_SCOPED_MODELS)


class ROLES(str, enum.Enum):
    OWNER = "owner"
    EMPLOYEE = "employee"
    BUSINESS_ADMIN = "business_admin"
    BRANCH_MANAGER = "branch_manager"

    @classmethod
    def choices(cls):
        return [
            (role.value, " ".join(role.value.split("_")).capitalize()) for role in cls
        ]


class Role(BaseModel):
    role_name = models.CharField(max_length=255, choices=ROLES.choices())
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
        blank=True,
        related_name="employees",
    )

    @property
    def full_name(self):
        full_name = self.user.first_name

        if self.user.last_name:
            full_name += f" {self.user.last_name}"
        return full_name

    def __str__(self):
        if self.user:
            return f"{self.user.email} - {self.role} at {self.business}"
        else:
            return f"Employee ID: {self.id}"


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

    class Meta:
        permissions = _generate_permissions("branch", BRANCH_SCOPED_MODELS)


def default_invitation_expiry():
    return timezone.now() + timedelta(days=7)


class EmployeeInvitation(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
    ]
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="pending")
    expires_at = models.DateTimeField(default=default_invitation_expiry)

    @property
    def is_expired(self):
        return self.status == "pending" and timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} - {self.business.name}"


# Business --> Branch -->Object Level Permissions
