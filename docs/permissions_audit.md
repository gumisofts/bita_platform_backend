# Permissions Audit — Bita Platform Backend

> Generated: May 17, 2026
> Branch: `dev-v01`
> Scope: `business`, `inventories`, `orders`, `finances`, `crms` apps

---

## 1. Architecture Overview

The platform uses **two parallel permission layers** that must both pass for access to be granted. Understanding both is critical for spotting gaps.

### Layer 1 — Role-level model permissions (`Role.permissions`)

Each `Role` object holds a Django `ManyToManyField` to `auth.Permission`. When a role is created, `assign_default_permissions_to_role()` in `business/signals.py` populates these based on model lists defined in `business/roles.py`.

These are checked in the legacy `has_business_permission` / `has_business_object_permission` helpers and `BusinessModelObjectPermission`.

```python
# business/models.py lines 231–237
class Role(BaseModel):
    role_name = models.CharField(max_length=255, choices=ROLES.choices())
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, ...)
```

### Layer 2 — Guardian object-level permissions (per-user, per-object)

When an employee joins a business (invitation accepted), `PermissionManager` in `business/permissions.py` calls `assign_perm()` (django-guardian) to grant specific codenames directly on the `Business` or `Branch` object.

These are checked in `BusinessLevelPermission`, `BranchLevelPermission`, and `GuardianObjectPermissions`, which are the permission classes actually wired into the active viewsets.

```python
# business/permissions.py lines 208–337
class PermissionManager:
    def assign_owner_permissions(self, user, business): ...
    def assign_business_admin_permissions(self, user, business): ...
    def assign_manager_permissions(self, user, business, branch): ...
    def assign_employee_permissions(self, user, business, branch): ...
```

### Permission codename convention

Custom permissions use a `<action>_<model>_<scope>` pattern where scope is either `_business` (applies across the whole business) or `_branch` (scoped to a specific branch).

```python
# business/models.py — Business.Meta.permissions
# e.g. "can_add_item_business", "can_view_order_branch"
permissions = [
    (perm.value[0] + "_business", perm.value[1])
    for perm in AdditionalBusinessPermissionNames
]
```

---

## 2. Roles

```python
# business/models.py lines 218–228
class ROLES(str, enum.Enum):
    OWNER         = "owner"
    EMPLOYEE      = "employee"
    BUSINESS_ADMIN = "business_admin"
    BRANCH_MANAGER = "branch_manager"
```

| Role | Code | Scope | Description |
|------|------|-------|-------------|
| **Owner** | `owner` | Business | Created automatically when a `Business` is created. The `Business.owner` FK user. Full control over all resources. |
| **Business Admin** | `business_admin` | Business | Manages the whole business — employees, inventory, orders, finances. No branch restriction. |
| **Branch Manager** | `branch_manager` | Branch | Manages a single branch. Requires a `branch` FK on `Employee`. |
| **Employee** | `employee` | Branch | Day-to-day operations. Requires a `branch` FK on `Employee`. |

> **Serializer enforces branch requirement:**
> ```python
> # business/serializers.py lines 141–147
> if role.role_name != ROLES.BUSINESS_ADMIN.value and branch is None:
>     raise ValidationError({"branch": "Branch is required for this role."})
> ```

---

## 3. Full Permission Matrix

Legend: `✅ full` = add + change + delete + view | `👁 view` = view only | `📝 add+change` = add + change (no delete) | `➕ add` = add only | `—` = no access

### 3.1 Owner

Assigned via `PermissionManager.assign_owner_permissions()` (Guardian, `_business` scope) and `assign_default_permissions_to_role()` for `OWNER` (all permissions on all `_OwnerFullAccessModels`).

```python
# business/permissions.py lines 217–222
def assign_owner_permissions(self, user, business):
    perms = [
        perm.value[0] + "_business" for perm in AdditionalBusinessPermissionNames
    ] + ["change_business", "delete_business", "view_business"]
    for perm in perms:
        assign_perm(perm, user, business)
```

```python
# business/roles.py lines 17–35
_OwnerFullAccessModels = [
    Business, Employee, Role, Branch, Address, Branch, BusinessActivity,
    BusinessImage, Item, Supply, Transaction, Order, BusinessPaymentMethod,
    ItemImage, EmployeeInvitation, InventoryMovement, InventoryMovementItem,
]
```

| Resource | Permission | Code | Description |
|----------|------------|------|-------------|
| Business | `✅ full` | `change_business`, `delete_business`, `view_business` | View, update, and delete the business entity itself |
| Branch | `✅ full` | `can_add_branch_business`, `can_change_branch_business`, `can_delete_branch_business`, `can_view_branch_business` | Full branch management at business level |
| Employee | `✅ full` | `can_add_employee_business`, `can_change_employee_business`, `can_delete_employee_business`, `can_view_employee_business` | Hire, fire, and reassign all employees |
| Role | `✅ full` | via `_OwnerFullAccessModels` | Create and modify roles and their permission sets |
| Address | `✅ full` | `can_add_address_business`, `can_change_address_business`, `can_delete_address_business`, `can_view_address_business` | Manage business and branch addresses |
| Employee Invitation | `✅ full` | `can_add_employeeinvitation_business`, `can_change_employeeinvitation_business`, `can_delete_employeeinvitation_business`, `can_view_employeeinvitation_business` | Send, revoke, and view all invitations |
| Item | `✅ full` | `can_add_item_business`, `can_change_item_business`, `can_delete_item_business`, `can_view_item_business` | Full product catalog management |
| Item Variant | `✅ full` | `can_add_itemvariant_business`, `can_change_itemvariant_business`, `can_delete_itemvariant_business`, `can_view_itemvariant_business` | Manage SKU variants (size, color, etc.) |
| Item Image | `✅ full` | via `_OwnerFullAccessModels` | Upload and delete product images |
| Group (category) | `✅ full` | `can_add_group_business`, `can_change_group_business`, `can_delete_group_business`, `can_view_group_business` | Manage item groupings/categories |
| Property | `✅ full` | `can_add_property_business`, `can_change_property_business`, `can_delete_property_business`, `can_view_property_business` | Manage custom item attribute definitions |
| Inventory | `✅ full` | `can_add_inventory_business`, `can_change_inventory_business`, `can_delete_inventory_business`, `can_view_inventory_business` | Manage inventory levels |
| Inventory Movement | `✅ full` | `can_add_inventorymovement_business`, `can_change_inventorymovement_business`, `can_delete_inventorymovement_business`, `can_view_inventorymovement_business` | Track stock transfers and adjustments |
| Supply (purchase) | `✅ full` | `can_add_supply_business`, `can_change_supply_business`, `can_delete_supply_business`, `can_view_supply_business` | Manage purchase/supply records |
| Supplier | `✅ full` | `can_add_supplier_business`, `can_change_supplier_business`, `can_delete_supplier_business`, `can_view_supplier_business` | Manage supplier directory |
| Order | `✅ full` | `can_add_order_business`, `can_change_order_business`, `can_delete_order_business`, `can_view_order_business` | Full order lifecycle management |
| Transaction | `✅ full` | `can_add_transaction_business`, `can_change_transaction_business`, `can_delete_transaction_business`, `can_view_transaction_business` | Full access to financial transactions |
| Payment Method | `✅ full` | `can_add_businesspaymentmethod_business`, `can_change_businesspaymentmethod_business`, `can_delete_businesspaymentmethod_business`, `can_view_businesspaymentmethod_business` | Configure accepted payment methods |
| Customer | `✅ full` | `can_add_customer_business`, `can_change_customer_business`, `can_delete_customer_business`, `can_view_customer_business` | Full CRM customer management |
| Gift Card | `✅ full` | `can_add_giftcard_business`, `can_change_giftcard_business`, `can_delete_giftcard_business`, `can_view_giftcard_business` | Issue and manage gift cards |
| Business Activity | `✅ full` | via `_OwnerFullAccessModels` | View and manage audit/activity logs |
| Business Image | `✅ full` | via `_OwnerFullAccessModels` | Manage business profile images |

---

### 3.2 Business Admin

Assigned via `PermissionManager.assign_business_admin_permissions()` (Guardian, `_business` scope) and `assign_default_permissions_to_role()` for `BUSINESS_ADMIN`.

```python
# business/permissions.py lines 210–215
def assign_business_admin_permissions(self, user, business):
    perms = [
        perm.value[0] + "_business" for perm in AdditionalBusinessPermissionNames
    ] + ["view_business", "change_business"]
    for perm in perms:
        assign_perm(perm, user, business)
```

```python
# business/roles.py lines 37–60
_AdminFullAccessModels = [
    Employee, Role, BusinessActivity, Address, Item, ItemImage,
    Order, EmployeeInvitation, InventoryMovement, InventoryMovementItem,
]
_AdminReadOnlyModels = [Business, Role, Branch]
```

| Resource | Permission | Code | Description |
|----------|------------|------|-------------|
| Business | `👁 view` + `change` | `view_business`, `change_business` | View and update business settings; **cannot delete** |
| Branch | `👁 view` | `view_branch` (role-level only) | Read-only branch info; **cannot create or delete branches** |
| Employee | `✅ full` | `can_add_employee_business`, `can_change_employee_business`, `can_delete_employee_business`, `can_view_employee_business` | Full staff management |
| Role | `✅ full` | via `_AdminFullAccessModels` | Can create and edit roles — ⚠️ see Gap #3 |
| Address | `✅ full` | `can_add_address_business`, `can_change_address_business`, `can_delete_address_business`, `can_view_address_business` | Manage addresses |
| Employee Invitation | `✅ full` | `can_add_employeeinvitation_business`, `can_change_employeeinvitation_business`, `can_delete_employeeinvitation_business`, `can_view_employeeinvitation_business` | Invite and manage invitations |
| Item | `✅ full` | `can_add_item_business`, `can_change_item_business`, `can_delete_item_business`, `can_view_item_business` | Full product catalog management |
| Item Variant | `✅ full` | `can_add_itemvariant_business`, `can_change_itemvariant_business`, `can_delete_itemvariant_business`, `can_view_itemvariant_business` | Manage variants |
| Item Image | `✅ full` | via `_AdminFullAccessModels` | Manage product images |
| Group | `✅ full` | `can_add_group_business`, `can_change_group_business`, `can_delete_group_business`, `can_view_group_business` | Manage item groups |
| Property | `✅ full` | `can_add_property_business`, `can_change_property_business`, `can_delete_property_business`, `can_view_property_business` | Manage item attributes |
| Inventory | `✅ full` | `can_add_inventory_business`, `can_change_inventory_business`, `can_delete_inventory_business`, `can_view_inventory_business` | Manage inventory |
| Inventory Movement | `✅ full` | `can_add_inventorymovement_business`, `can_change_inventorymovement_business`, `can_delete_inventorymovement_business`, `can_view_inventorymovement_business` | Track stock movement |
| Supply | `✅ full` | `can_add_supply_business`, `can_change_supply_business`, `can_delete_supply_business`, `can_view_supply_business` | Manage purchase records |
| Supplier | `✅ full` | `can_add_supplier_business`, `can_change_supplier_business`, `can_delete_supplier_business`, `can_view_supplier_business` | Manage suppliers |
| Order | `✅ full` | `can_add_order_business`, `can_change_order_business`, `can_delete_order_business`, `can_view_order_business` | Full order management |
| Transaction | `✅ full` | `can_add_transaction_business`, `can_change_transaction_business`, `can_delete_transaction_business`, `can_view_transaction_business` | Financial records |
| Payment Method | `✅ full` | `can_add_businesspaymentmethod_business`, ..., `can_view_businesspaymentmethod_business` | Configure payment methods |
| Customer | `✅ full` | `can_add_customer_business`, `can_change_customer_business`, `can_delete_customer_business`, `can_view_customer_business` | Full CRM access |
| Gift Card | `✅ full` | `can_add_giftcard_business`, `can_change_giftcard_business`, `can_delete_giftcard_business`, `can_view_giftcard_business` | Manage gift cards |
| Business Activity | `✅ full` | via `_AdminFullAccessModels` | View and write audit logs — ⚠️ see Gap #5 |

---

### 3.3 Branch Manager

Assigned via `PermissionManager.assign_manager_permissions()` (Guardian, `_branch` scope) and `assign_default_permissions_to_role()` for `BRANCH_MANAGER`.

```python
# business/permissions.py lines 224–291
def assign_manager_permissions(self, user, business, branch):
    branch_manager_perms = [
        CAN_VIEW_GROUP, CAN_ADD_GROUP, CAN_CHANGE_GROUP,
        CAN_VIEW_CUSTOMER, CAN_ADD_CUSTOMER, CAN_CHANGE_CUSTOMER,
        CAN_VIEW_ITEM, CAN_ADD_ITEM, CAN_CHANGE_ITEM,
        CAN_VIEW_ITEM_VARIANT, CAN_ADD_ITEM_VARIANT, CAN_CHANGE_ITEM_VARIANT,
        CAN_VIEW_SUPPLIER, CAN_ADD_SUPPLIER, CAN_CHANGE_SUPPLIER,
        CAN_VIEW_INVENTORY, CAN_ADD_INVENTORY,
        CAN_VIEW_INVENTORY_MOVEMENT, CAN_ADD_INVENTORY_MOVEMENT,
        CAN_VIEW_ORDER, CAN_ADD_ORDER, CAN_CHANGE_ORDER,
        CAN_VIEW_TRANSACTION, CAN_ADD_TRANSACTION,
        CAN_VIEW_BUSINESS_PAYMENT_METHOD, CAN_CHANGE_BUSINESS_PAYMENT_METHOD,
        CAN_VIEW_PROPERTY, CAN_ADD_PROPERTY, CAN_CHANGE_PROPERTY,
        CAN_VIEW_SUPPLY, CAN_ADD_SUPPLY,
        CAN_VIEW_EMPLOYEE, CAN_VIEW_EMPLOYEE_INVITATION, CAN_ADD_EMPLOYEE_INVITATION,
    ]
    # plus: view_branch, add_branch, change_branch, view_business
```

| Resource | Permission | Code | Description |
|----------|------------|------|-------------|
| Business | `👁 view` | `view_business` | Read-only business info |
| Branch | `📝 add+change` | `view_branch`, `add_branch`, `change_branch` | View and update their branch — ⚠️ add_branch seems overly broad (see Gap #6) |
| Employee | `👁 view` | `can_view_employee_branch` | See employees in their branch |
| Employee Invitation | `➕ add` + `👁 view` | `can_add_employeeinvitation_branch`, `can_view_employeeinvitation_branch` | Invite new employees to branch |
| Item | `📝 add+change` | `can_view_item_branch`, `can_add_item_branch`, `can_change_item_branch` | Manage products for their branch |
| Item Variant | `📝 add+change` | `can_view_itemvariant_branch`, `can_add_itemvariant_branch`, `can_change_itemvariant_branch` | Manage variants |
| Group | `📝 add+change` | `can_view_group_branch`, `can_add_group_branch`, `can_change_group_branch` | Manage groupings |
| Property | `📝 add+change` | `can_view_property_branch`, `can_add_property_branch`, `can_change_property_branch` | Manage item attributes |
| Inventory | `➕ add` + `👁 view` | `can_view_inventory_branch`, `can_add_inventory_branch` | View and record stock levels |
| Inventory Movement | `➕ add` + `👁 view` | `can_view_inventorymovement_branch`, `can_add_inventorymovement_branch` | Record stock transfers |
| Supply | `➕ add` + `👁 view` | `can_view_supply_branch`, `can_add_supply_branch` | Create purchase/supply records |
| Supplier | `📝 add+change` | `can_view_supplier_branch`, `can_add_supplier_branch`, `can_change_supplier_branch` | Manage supplier contacts |
| Order | `📝 add+change` | `can_view_order_branch`, `can_add_order_branch`, `can_change_order_branch` | Process and update orders |
| Transaction | `➕ add` + `👁 view` | `can_view_transaction_branch`, `can_add_transaction_branch` | Record and view payments |
| Payment Method | `change` + `👁 view` | `can_view_businesspaymentmethod_branch`, `can_change_businesspaymentmethod_branch` | View and update payment methods |
| Customer | `📝 add+change` | `can_view_customer_branch`, `can_add_customer_branch`, `can_change_customer_branch` | Manage branch customers |
| Gift Card | `—` | *(none assigned)* | ⚠️ No gift card access — see Gap #4 |
| Address | `—` | *(none assigned)* | ⚠️ No address access — see Gap #7 |
| Role | `👁 view` (role-level only) | via `_AdminReadOnlyModels` | ⚠️ Role-level read via admin models; no guardian perm assigned |
| Business Activity | `✅ full` (role-level only) | via `_AdminFullAccessModels` | ⚠️ Full write to audit logs — see Gap #5 |

---

### 3.4 Employee

Assigned via `PermissionManager.assign_employee_permissions()` (Guardian, `_branch` scope) and `assign_default_permissions_to_role()` for `EMPLOYEE`.

```python
# business/permissions.py lines 293–337
def assign_employee_permissions(self, user, business, branch):
    employee_branch_perms = [
        CAN_VIEW_GROUP,
        CAN_VIEW_CUSTOMER, CAN_ADD_CUSTOMER,
        CAN_VIEW_ITEM,
        CAN_VIEW_ITEM_VARIANT, CAN_ADD_ITEM_VARIANT,
        CAN_VIEW_SUPPLIER,
        CAN_VIEW_INVENTORY, CAN_VIEW_INVENTORY_MOVEMENT, CAN_ADD_INVENTORY_MOVEMENT,
        CAN_VIEW_ORDER, CAN_ADD_ORDER, CAN_CHANGE_ORDER,
        CAN_VIEW_TRANSACTION, CAN_ADD_TRANSACTION,
        CAN_VIEW_BUSINESS_PAYMENT_METHOD,
        CAN_VIEW_PROPERTY,
        CAN_VIEW_SUPPLY,
    ]
    # plus: view_branch, view_business
```

```python
# business/roles.py lines 50–66
_EmployeeFullAccessModels = [Item, Business, Supply, Transaction, Order, ItemImage, InventoryMovement]
_EmployeeReadOnlyModels   = [Business, Employee, User, Role]
```

| Resource | Permission | Code | Description |
|----------|------------|------|-------------|
| Business | `👁 view` | `view_business` | Read-only business info |
| Branch | `👁 view` | `view_branch` | View their assigned branch |
| Employee | `👁 view` | via `_EmployeeReadOnlyModels` | View co-worker list |
| Role | `👁 view` | via `_EmployeeReadOnlyModels` | View role definitions |
| Item | `👁 view` | `can_view_item_branch` | Browse product catalog |
| Item Variant | `➕ add` + `👁 view` | `can_view_itemvariant_branch`, `can_add_itemvariant_branch` | View variants; can add new ones — ⚠️ see Gap #10 |
| Item Image | `✅ full` (role-level) | via `_EmployeeFullAccessModels` | ⚠️ Role-level full CRUD but no guardian perm — see Gap #11 |
| Group | `👁 view` | `can_view_group_branch` | View groupings |
| Property | `👁 view` | `can_view_property_branch` | View attributes |
| Inventory | `👁 view` | `can_view_inventory_branch` | View stock levels |
| Inventory Movement | `➕ add` + `👁 view` | `can_view_inventorymovement_branch`, `can_add_inventorymovement_branch` | Record stock adjustments |
| Supply | `👁 view` | `can_view_supply_branch` | View purchases — ⚠️ role-level has full CRUD, see Gap #8 |
| Supplier | `👁 view` | `can_view_supplier_branch` | View supplier list |
| Order | `📝 add+change` | `can_view_order_branch`, `can_add_order_branch`, `can_change_order_branch` | Create and process orders |
| Transaction | `➕ add` + `👁 view` | `can_view_transaction_branch`, `can_add_transaction_branch` | Record sales transactions |
| Payment Method | `👁 view` | `can_view_businesspaymentmethod_branch` | View available payment options |
| Customer | `➕ add` + `👁 view` | `can_view_customer_branch`, `can_add_customer_branch` | View and add customers; **cannot edit** |
| Gift Card | `—` | *(none assigned)* | ⚠️ No gift card access — see Gap #4 |
| Address | `—` | *(none assigned)* | ⚠️ No address access — see Gap #7 |
| Employee Invitation | `—` | *(none assigned)* | View own invitations via `IsAuthenticated`-only `mine` action |
| Business Activity | `—` | *(none assigned)* | Cannot view any audit logs |

---

## 4. Gaps & Caveats

### Gap #1 — Branch Manager is a copy-paste of Business Admin (role-level)

**Severity: High**

`signals.py` lines 49–62 explicitly use `_AdminFullAccessModels` and `_AdminReadOnlyModels` for `BRANCH_MANAGER` — the same lists as Business Admin:

```python
# business/signals.py lines 49–62
elif role.role_name == ROLES.BRANCH_MANAGER.value:
    # Branch Manager: Similar to Business Admin but with branch-specific permissions
    # For now, use Admin permissions as a base  ← TODO comment in code
    for model in roles._AdminFullAccessModels:
        ...
    for model in roles._AdminReadOnlyModels:
        ...
```

At the **role model permission** level (Layer 1) a Branch Manager is indistinguishable from a Business Admin. While Guardian (Layer 2) correctly scopes them to a branch, there is no dedicated `_BranchManagerFullAccessModels` list. The comment "For now, use Admin permissions as a base" confirms this is unfinished.

**Fix:** Create `_BranchManagerFullAccessModels` and `_BranchManagerReadOnlyModels` in `roles.py` and update `assign_default_permissions_to_role`.

---

### Gap #2 — Employee role-level permissions include full CRUD on `Business`

**Severity: High**

`_EmployeeFullAccessModels` contains `Business`:

```python
# business/roles.py lines 50–58
_EmployeeFullAccessModels = [
    Item,
    Business,   # ← full add/change/delete at role level
    Supply,
    Transaction,
    Order,
    ItemImage,
    InventoryMovement,
]
```

This grants every `employee` role `add_business`, `change_business`, and `delete_business` at the **model permission** level. Guardian (Layer 2) only grants `view_business`, so the Guardian check would stop a request in practice — but this is fragile. Any view that uses only Layer 1 checks (e.g. `BusinessModelObjectPermission` or the legacy `has_business_permission` helpers) would silently allow employees to mutate or delete the business object.

**Fix:** Remove `Business` from `_EmployeeFullAccessModels`. Add it to `_EmployeeReadOnlyModels` instead (it's already there — the duplicate causes no harm but the full-access entry overrides it).

---

### Gap #3 — Business Admin can modify `Role` permissions (privilege escalation risk)

**Severity: High**

`_AdminFullAccessModels` includes `Role`:

```python
# business/roles.py lines 37–48
_AdminFullAccessModels = [
    Employee,
    Role,   # ← full CRUD including change
    BusinessActivity,
    ...
]
```

A Business Admin can `PATCH /roles/{id}/` to add any permission (including owner-level ones) to their own role, effectively self-escalating to full owner access. The `BusinessRoleViewset` uses `BusinessLevelPermission | BranchLevelPermission` with no additional ownership check.

**Fix:** Remove `Role` from `_AdminFullAccessModels`. Business Admins should be able to **view** roles (already in `_AdminReadOnlyModels`) but only the **Owner** should be able to create/edit role permission sets.

---

### Gap #4 — Gift Card permissions not assigned to Branch Manager or Employee

**Severity: Medium**

`AdditionalBusinessPermissionNames` defines gift card permissions:

```python
# business/models.py lines 129–132
CAN_ADD_GIFT_CARD    = ("can_add_giftcard", "Can add gift card")
CAN_CHANGE_GIFT_CARD = ("can_change_giftcard", "Can change gift card")
CAN_DELETE_GIFT_CARD = ("can_delete_giftcard", "Can delete gift card")
CAN_VIEW_GIFT_CARD   = ("can_view_giftcard", "Can view gift card")
```

Neither `assign_manager_permissions` nor `assign_employee_permissions` in `PermissionManager` assigns any of these. Branch managers and employees cannot view or issue gift cards at all. Owner and Business Admin receive them only because their methods loop over **all** `AdditionalBusinessPermissionNames`.

**Fix:** Add gift card view + add to `assign_manager_permissions`. Add gift card view (at minimum) to `assign_employee_permissions` so employees can accept them at checkout.

---

### Gap #5 — Business Activity logs are writable by Admin and Branch Manager

**Severity: Medium**

`_AdminFullAccessModels` includes `BusinessActivity` (full CRUD). This means a Business Admin or Branch Manager can `DELETE` or `PATCH` audit log entries — defeating the audit trail.

```python
# business/roles.py lines 37–48
_AdminFullAccessModels = [
    ...
    BusinessActivity,   # ← full delete/change
    ...
]
```

**Fix:** Move `BusinessActivity` out of `_AdminFullAccessModels` entirely. Add it to a read-only model list for all non-owner roles. Only the Owner (and `is_staff`/`is_superuser`) should ever modify activity logs.

---

### Gap #6 — Branch Manager can create new branches (`add_branch`)

**Severity: Medium**

`assign_manager_permissions` grants `add_branch` on the user's branch object:

```python
# business/permissions.py lines 278–291
branch_perms = [
    "view_branch",
    "add_branch",    # ← a manager can register entirely new branches
    "change_branch",
]
for perm in branch_perms:
    assign_perm(perm, user, branch)
```

Creating a new branch is a business-level decision, not a branch-level one. Granting it to a manager is also semantically incorrect — `assign_perm` on a specific `branch` object for `add_branch` (a model-level action, not object-level) behaves unpredictably with Guardian.

**Fix:** Remove `add_branch` from `branch_perms` in `assign_manager_permissions`. Branch creation should remain exclusive to Owner and Business Admin.

---

### Gap #7 — No address permissions for Branch Manager or Employee

**Severity: Medium**

Neither `assign_manager_permissions` nor `assign_employee_permissions` includes any `CAN_*_ADDRESS` permission. Branch managers cannot update their branch's address. Employees cannot view stored addresses (e.g. for delivery orders).

```python
# Neither method includes any of these:
# CAN_VIEW_ADDRESS, CAN_ADD_ADDRESS, CAN_CHANGE_ADDRESS, CAN_DELETE_ADDRESS
```

**Fix:** Add `CAN_VIEW_ADDRESS` + `CAN_CHANGE_ADDRESS` to `assign_manager_permissions`. Add `CAN_VIEW_ADDRESS` to `assign_employee_permissions` if address display is needed for order fulfillment.

---

### Gap #8 — Inconsistency between Layer 1 and Layer 2 for Employee `Supply`

**Severity: Medium**

`_EmployeeFullAccessModels` (Layer 1) gives employees full CRUD on `Supply`, but `assign_employee_permissions` (Layer 2) only grants `CAN_VIEW_SUPPLY`:

```python
# Layer 1 (roles.py) — employee has full add/change/delete/view on Supply
_EmployeeFullAccessModels = [..., Supply, ...]

# Layer 2 (permissions.py) — employee only has view
employee_branch_perms = [
    ...
    CAN_VIEW_SUPPLY,   # ← no add/change/delete
    ...
]
```

Since most views use Guardian (Layer 2), the effective permission is view-only. However, any view using Layer 1 checks would allow employees to create or delete supply records.

**Decide:** Should employees be able to create supply/purchase records? If yes, add `CAN_ADD_SUPPLY` to `assign_employee_permissions`. If no, remove `Supply` from `_EmployeeFullAccessModels`.

---

### Gap #9 — Inconsistency: Employee `Transaction` full CRUD in Layer 1 but only view+add in Layer 2

**Severity: Medium**

Same pattern as Gap #8:

```python
# Layer 1 — full CRUD
_EmployeeFullAccessModels = [..., Transaction, ...]

# Layer 2 — only view + add
employee_branch_perms = [
    CAN_VIEW_TRANSACTION,
    CAN_ADD_TRANSACTION,
    # no CAN_CHANGE_TRANSACTION, no CAN_DELETE_TRANSACTION
]
```

Should an employee be able to modify or delete a transaction? Typically no — financial records need to be immutable once created.

**Fix:** Remove `Transaction` from `_EmployeeFullAccessModels` and add it to `_EmployeeReadOnlyModels` (since they already have `CAN_VIEW_TRANSACTION`). The Layer 2 `CAN_ADD_TRANSACTION` covers the cashier use case.

---

### Gap #10 — Employee can add `ItemVariant` but only view `Item`

**Severity: Low-Medium**

An employee can `POST /item-variants/` (add new variant) but cannot `PATCH /items/` (change the parent item). A variant without the ability to even edit the parent item's base fields is an awkward split.

```python
# assign_employee_permissions
CAN_VIEW_ITEM,                         # view only
CAN_VIEW_ITEM_VARIANT, CAN_ADD_ITEM_VARIANT,   # but can create variants
```

**Consider:** Either also grant `CAN_CHANGE_ITEM` to employees (if editing product details is part of their role), or remove `CAN_ADD_ITEM_VARIANT` from employees and make it manager-only.

---

### Gap #11 — Employee has role-level full CRUD on `ItemImage` but no Guardian object permission

**Severity: Low-Medium**

`_EmployeeFullAccessModels` includes `ItemImage` but `assign_employee_permissions` has no `ItemImage` entries. Since active views use Guardian (`GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission`), employees cannot upload or delete item images in practice. But via the legacy `BusinessModelObjectPermission` they would have access.

**Fix:** Either add explicit item image permissions to `assign_employee_permissions` if upload is intended, or remove `ItemImage` from `_EmployeeFullAccessModels`.

---

### Gap #12 — `InventoryMovementItem` missing from Employee role models

**Severity: Low**

`_EmployeeFullAccessModels` includes `InventoryMovement` (the movement header) but not `InventoryMovementItem` (the line items). Creating an `InventoryMovement` requires also creating `InventoryMovementItem` rows:

```python
# Missing from Employee:
_OwnerFullAccessModels = [..., InventoryMovement, InventoryMovementItem]  # ← owner has both
_AdminFullAccessModels = [..., InventoryMovement, InventoryMovementItem]  # ← admin has both
_EmployeeFullAccessModels = [..., InventoryMovement]                       # ← employee missing InventoryMovementItem
```

**Fix:** Add `InventoryMovementItem` to `_EmployeeFullAccessModels`.

---

### Gap #13 — `add_business` not granted to Owner in `assign_owner_permissions`

**Severity: Low / Informational**

`assign_owner_permissions` gives the owner `change_business`, `delete_business`, `view_business` but not `add_business`. The ability to create a new business is separately granted to all verified users via:

```python
# accounts/signals.py lines 8–14
@receiver(user_verified)
def on_user_verified(sender, user, mode, **kwargs):
    ...
    assign_perm("business.add_business", user)
```

This means any verified user (including employees) can create a new business. This is likely intentional but worth documenting explicitly.

---

### Gap #14 — Owner invitation missing from `on_employee_invitation_status_changed`

**Severity: Low / Informational**

The signal handler only assigns Guardian permissions for `BUSINESS_ADMIN`, `EMPLOYEE`, and `BRANCH_MANAGER`:

```python
# business/signals.py lines 179–190
if instance.role.role_name == ROLES.BUSINESS_ADMIN.value:
    PermissionManager().assign_business_admin_permissions(...)
elif instance.role.role_name == ROLES.EMPLOYEE.value:
    PermissionManager().assign_employee_permissions(...)
elif instance.role.role_name == ROLES.BRANCH_MANAGER.value:
    PermissionManager().assign_manager_permissions(...)
# ← no case for ROLES.OWNER
```

If an `EmployeeInvitation` is created with role `owner` (nothing prevents this at the model level), the invited user joins as an employee record with the owner role but receives **no Guardian object permissions**. They would have role-level permissions but all Guardian-gated views would return 403.

**Fix:** Add an `elif instance.role.role_name == ROLES.OWNER.value:` branch calling `PermissionManager().assign_owner_permissions(...)`, or add a model-level constraint preventing owner-role invitations.

---

### Gap #15 — Seed script uses arbitrary role names bypassing ROLES enum

**Severity: Low / Testing**

`core/management/commands/seed_db.py` creates roles with names like `"Manager"`, `"Cashier"`, `"Sales Associate"` that don't match any `ROLES` enum value:

```python
# seed_db.py lines 620–633
role_names = ["Manager", "Cashier", "Sales Associate", "Inventory Manager", "Admin"]
for role_name in role_names:
    role = Role.objects.create(role_name=role_name, business=business)
```

These roles get random permissions from `Permission.objects.all()` — not the real business permission set. The `Role.role_name` field has `choices=ROLES.choices()` which Django only validates at the form/serializer layer, not the DB layer, so the seed bypasses it. This pollutes test/dev data.

**Fix:** Restrict seed to valid `ROLES` values, or add a `CheckConstraint` / validator to `Role.role_name`.

---

### Gap #16 — Two permission layers can fall out of sync

**Severity: Architectural**

Layer 1 (`Role.permissions`) and Layer 2 (Guardian per-user/per-object) are assigned independently at different lifecycle events:

- Layer 1 fires on `Role` `post_save` (signal)
- Layer 2 fires on invitation acceptance (signal)

If an admin manually changes `Role.permissions` in the Django admin after invitation acceptance, Layer 2 Guardian permissions are **not updated**. Conversely, re-assigning an employee to a different branch updates their role FK but does **not** revoke old Guardian permissions or grant new ones.

**Fix:** Either unify the system (use only Guardian or only role-based), or add a `post_save` signal on `Employee` that calls `remove_perm` for old scope and `assign_perm` for new scope whenever `branch` or `role` changes.

---

## 5. Summary Table

| # | Gap | Affected Roles | Severity |
|---|-----|---------------|----------|
| 1 | Branch Manager identical to Business Admin at role level | `branch_manager` | 🔴 High |
| 2 | Employee has full CRUD on `Business` at role level | `employee` | 🔴 High |
| 3 | Business Admin can escalate own role permissions | `business_admin` | 🔴 High |
| 4 | Gift cards inaccessible to Branch Manager and Employee | `branch_manager`, `employee` | 🟡 Medium |
| 5 | Activity logs are writable by Admin and Branch Manager | `business_admin`, `branch_manager` | 🟡 Medium |
| 6 | Branch Manager can create new branches | `branch_manager` | 🟡 Medium |
| 7 | No address permissions for Branch Manager or Employee | `branch_manager`, `employee` | 🟡 Medium |
| 8 | Employee Supply: full CRUD in Layer 1, view-only in Layer 2 | `employee` | 🟡 Medium |
| 9 | Employee Transaction: full CRUD in Layer 1, view+add in Layer 2 | `employee` | 🟡 Medium |
| 10 | Employee can add `ItemVariant` but not change parent `Item` | `employee` | 🟠 Low-Medium |
| 11 | Employee `ItemImage` full CRUD in Layer 1, no Guardian perm | `employee` | 🟠 Low-Medium |
| 12 | `InventoryMovementItem` missing from Employee role models | `employee` | 🟢 Low |
| 13 | `add_business` not granted to Owner in `assign_owner_permissions` | `owner` | 🟢 Informational |
| 14 | No Guardian permissions assigned for Owner invitations | `owner` | 🟢 Low |
| 15 | Seed script uses non-enum role names bypassing `choices` | all | 🟢 Low (dev) |
| 16 | Two permission layers can fall out of sync | all | 🔵 Architectural |

---

## 6. Relevant Source Files

| File | Purpose |
|------|---------|
| `business/models.py` | `AdditionalBusinessPermissionNames` enum, `ROLES` enum, `Role` model, `Business.Meta.permissions` |
| `business/roles.py` | Model lists used to populate role-level permissions |
| `business/signals.py` | `assign_default_permissions_to_role()`, `on_business_created`, `on_employee_invitation_status_changed` |
| `business/permissions.py` | `PermissionManager`, all DRF permission classes, Guardian integration |
| `business/views.py` | View-level `permission_classes` per endpoint |
| `business/middleware.py` | Sets `request.business` / `request.branch` context |
| `accounts/signals.py` | Grants `add_business` to all verified users |
| `finances/views.py` | `has_perm` inline checks for transaction/financial report access |
| `orders/views.py` | `has_perm` inline checks for order scoping |
| `inventories/views.py` | `has_perm` inline checks for item/supply scoping |
| `crms/views.py` | Customer and gift card permission classes |
