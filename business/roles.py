from accounts.models import *
from business.models import *
from crms.models import *
from financials.models import *
from inventories.models import *
from notifications.models import *
from orders.models import *

# Discreate Roles mode
# Owner
# Admin
# Employee


OwnerFullAccessModels = [
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
]

AdminFullAccessModels = [
    Employee,
    Role,
    BusinessActivity,
    Address,
    Item,
    ItemImage,
    Order,
    EmployeeInvitation,
]

EmployeeFullAccessModels = [
    Item,
    Business,
    Supply,
    Transaction,
    Order,
    ItemImage,
]

AdminReadOnlyModels = [Business, Role, Branch]
EmployeeReadOnlyModels = [
    Business,
    Employee,
    User,
    Role,
]

#
