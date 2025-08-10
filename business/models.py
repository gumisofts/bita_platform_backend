import enum
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.validators import RegexValidator
from django.db import models

from core.models import BaseModel

User = get_user_model()


class AdditionalBusinessPermissionNames(enum.Enum):

    CAN_ADD_BRANCH = ("can_add_branch", "Can add branch")
    CAN_CHANGE_BRANCH = ("can_change_branch", "Can change branch")
    CAN_DELETE_BRANCH = ("can_delete_branch", "Can delete branch")
    CAN_VIEW_BRANCH = ("can_view_branch", "Can view branch")

    CAN_ADD_EMPLOYEE = ("can_add_employee", "Can add employee")
    CAN_CHANGE_EMPLOYEE = ("can_change_employee", "Can change employee")
    CAN_DELETE_EMPLOYEE = ("can_delete_employee", "Can delete employee")
    CAN_VIEW_EMPLOYEE = ("can_view_employee", "Can view employee")

    CAN_ADD_ADDRESS = ("can_add_address", "Can add address")
    CAN_CHANGE_ADDRESS = ("can_change_address", "Can change address")
    CAN_DELETE_ADDRESS = ("can_delete_address", "Can delete address")
    CAN_VIEW_ADDRESS = ("can_view_address", "Can view address")

    CAN_ADD_EMPLOYEE_INVITATION = (
        "can_add_employeeinvitation",
        "Can add employee invitation",
    )
    CAN_CHANGE_EMPLOYEE_INVITATION = (
        "can_change_employeeinvitation",
        "Can change employee invitation",
    )
    CAN_DELETE_EMPLOYEE_INVITATION = (
        "can_delete_employeeinvitation",
        "Can delete employee invitation",
    )
    CAN_VIEW_EMPLOYEE_INVITATION = (
        "can_view_employeeinvitation",
        "Can view employee invitation",
    )

    CAN_ADD_GROUP = ("can_add_group", "Can add group")
    CAN_CHANGE_GROUP = ("can_change_group", "Can change group")
    CAN_DELETE_GROUP = ("can_delete_group", "Can delete group")
    CAN_VIEW_GROUP = ("can_view_group", "Can view group")

    CAN_ADD_ORDER = ("can_add_order", "Can add order")
    CAN_CHANGE_ORDER = ("can_change_order", "Can change order")
    CAN_DELETE_ORDER = ("can_delete_order", "Can delete order")
    CAN_VIEW_ORDER = ("can_view_order", "Can view order")

    CAN_ADD_ITEM = ("can_add_item", "Can add item")
    CAN_CHANGE_ITEM = ("can_change_item", "Can change item")
    CAN_DELETE_ITEM = ("can_delete_item", "Can delete item")
    CAN_VIEW_ITEM = ("can_view_item", "Can view item")

    CAN_ADD_INVENTORY_MOVEMENT = (
        "can_add_inventorymovement",
        "Can add inventory movement",
    )
    CAN_CHANGE_INVENTORY_MOVEMENT = (
        "can_change_inventorymovement",
        "Can change inventory movement",
    )
    CAN_DELETE_INVENTORY_MOVEMENT = (
        "can_delete_inventorymovement",
        "Can delete inventory movement",
    )
    CAN_VIEW_INVENTORY_MOVEMENT = (
        "can_view_inventorymovement",
        "Can view inventory movement",
    )

    CAN_ADD_INVENTORY = ("can_add_inventory", "Can add inventory")
    CAN_CHANGE_INVENTORY = ("can_change_inventory", "Can change inventory")
    CAN_DELETE_INVENTORY = ("can_delete_inventory", "Can delete inventory")
    CAN_VIEW_INVENTORY = ("can_view_inventory", "Can view inventory")

    CAN_ADD_PROPERTY = ("can_add_property", "Can add property")
    CAN_CHANGE_PROPERTY = ("can_change_property", "Can change property")
    CAN_DELETE_PROPERTY = ("can_delete_property", "Can delete property")
    CAN_VIEW_PROPERTY = ("can_view_property", "Can view property")

    CAN_ADD_ITEM_VARIANT = ("can_add_itemvariant", "Can add item variant")
    CAN_CHANGE_ITEM_VARIANT = ("can_change_itemvariant", "Can change item variant")
    CAN_DELETE_ITEM_VARIANT = ("can_delete_itemvariant", "Can delete item variant")
    CAN_VIEW_ITEM_VARIANT = ("can_view_itemvariant", "Can view item variant")

    CAN_ADD_SUPPLIER = ("can_add_supplier", "Can add supplier")
    CAN_CHANGE_SUPPLIER = ("can_change_supplier", "Can change supplier")
    CAN_DELETE_SUPPLIER = ("can_delete_supplier", "Can delete supplier")
    CAN_VIEW_SUPPLIER = ("can_view_supplier", "Can view supplier")

    CAN_ADD_CUSTOMER = ("can_add_customer", "Can add customer")
    CAN_CHANGE_CUSTOMER = ("can_change_customer", "Can change customer")
    CAN_DELETE_CUSTOMER = ("can_delete_customer", "Can delete customer")
    CAN_VIEW_CUSTOMER = ("can_view_customer", "Can view customer")

    CAN_ADD_BUSINESS_PAYMENT_METHOD = (
        "can_add_businesspaymentmethod",
        "Can add business payment method",
    )
    CAN_CHANGE_BUSINESS_PAYMENT_METHOD = (
        "can_change_businesspaymentmethod",
        "Can change business payment method",
    )
    CAN_DELETE_BUSINESS_PAYMENT_METHOD = (
        "can_delete_businesspaymentmethod",
        "Can delete business payment method",
    )
    CAN_VIEW_BUSINESS_PAYMENT_METHOD = (
        "can_view_businesspaymentmethod",
        "Can view business payment method",
    )

    CAN_ADD_TRANSACTION = ("can_add_transaction", "Can add transaction")
    CAN_CHANGE_TRANSACTION = ("can_change_transaction", "Can change transaction")
    CAN_DELETE_TRANSACTION = ("can_delete_transaction", "Can delete transaction")
    CAN_VIEW_TRANSACTION = ("can_view_transaction", "Can view transaction")

    CAN_ADD_GIFT_CARD = ("can_add_giftcard", "Can add gift card")
    CAN_CHANGE_GIFT_CARD = ("can_change_giftcard", "Can change gift card")
    CAN_DELETE_GIFT_CARD = ("can_delete_giftcard", "Can delete gift card")
    CAN_VIEW_GIFT_CARD = ("can_view_giftcard", "Can view gift card")

    CAN_ADD_SUPPLY = ("can_add_supply", "Can add supply")
    CAN_CHANGE_SUPPLY = ("can_change_supply", "Can change supply")
    CAN_DELETE_SUPPLY = ("can_delete_supply", "Can delete supply")
    CAN_VIEW_SUPPLY = ("can_view_supply", "Can view supply")


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

    def __str__(self):
        return self.name

    class Meta:
        permissions = [
            (perm.value[0] + "_business", perm.value[1])
            for perm in AdditionalBusinessPermissionNames
        ]


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
        permissions = [
            (perm.value[0] + "_branch", perm.value[1])
            for perm in AdditionalBusinessPermissionNames
        ]


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

    def __str__(self):
        return f"{self.email} - {self.business.name}"


# Business --> Branch -->Object Level Permissions
