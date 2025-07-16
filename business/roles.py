from accounts.models import *
from business.models import *
from crms.models import *
from financials.models import *
from inventories.models import *
from notifications.models import *
from orders.models import *

# Business Roles Permissions are applied here

# Discreate Roles mode
# Owner
# Admin
# Employee


_OwnerFullAccessModels = [
    Business,
    Employee,
    Role,
    Branch,
    Address,
    Branch,
    BusinessActivity,
    BusinessImage,
    Item,
    Supply,
    Transaction,
    Order,
    BusinessPaymentMethod,
    ItemImage,
    EmployeeInvitation,
    InventoryMovement,
    InventoryMovementItem,
]

_AdminFullAccessModels = [
    Employee,
    Role,
    BusinessActivity,
    Address,
    Item,
    ItemImage,
    Order,
    EmployeeInvitation,
    InventoryMovement,
    InventoryMovementItem,
]

_EmployeeFullAccessModels = [
    Item,
    Business,
    Supply,
    Transaction,
    Order,
    ItemImage,
    InventoryMovement,
]

_AdminReadOnlyModels = [Business, Role, Branch]
_EmployeeReadOnlyModels = [
    Business,
    Employee,
    User,
    Role,
]

# Owner Full Access Models

# OwnerPermissionsStrings = list(
#     _OwnerFullAccessModels.map(
#         lambda item: f"{item._meta.app_label}.view_{item._meta.model_name}"
#     )
# )

# AdminPermissionsStrings = list(
#     _AdminFullAccessModels(
#         lambda item: f"{item._meta.app_label}.view_{item._meta.model_name}"
#     )
# )


# EmployeePermissionsStrings = list(
#     _EmployeeFullAccessModels.map(
#         lambda item: f"{item._meta.app_label}.view_{item._meta.model_name}"
#     )
# )


# Owner Should Have Full Access to all objects in the business Context
# Manager Should Have Read Only Access to all objects in the business Context
# Employee Should Have Read Only Access to all objects in the business Context
# Anyone who created an object should have full access to that object in the business Context
