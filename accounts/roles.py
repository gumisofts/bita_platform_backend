from accounts.models import *
from crms.models import *
from inventories.models import *
from notifications.models import *
from financials.models import *


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
]

AdminFullAccessModels = [
    Employee,
    Role,
    BusinessActivity,
    Address,
    Item,
    ItemImage,
    Order,
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
