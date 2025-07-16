# Project Permission System Documentation

## Overview

This document outlines the permission structure implemented in the project. The system is organized into three primary levels of access control:

1. Business-Level Permissions
2. Branch-Level Permissions
3. Object-Level Permissions

Each level supports standard actions (`view`, `add`, `change`, `delete`) and follows strict naming conventions to maintain clarity and consistency.

---

## 1. Business-Level Permissions

### Scope

These permissions govern access and actions related to the entire business entity. They are typically assigned to users with organization-wide responsibilities.

### Allowed Actions

- `can_view_inventory`
- `can_add_inventory`
- `can_change_inventory`
- `can_delete_inventory`

### Naming Convention

```
<action>_business
```

### Examples

- `can_view_inventory_business`
- `can_add_inventory_business`
- `can_change_inventory_business`
- `can_delete_inventory_business`

---

## 2. Branch-Level Permissions

### Scope

These permissions control access at the branch level of a business. Each branch within a business can have specific users with assigned permissions.

### Allowed Actions examples

- `can_view_inventory`
- `can_add_inventory`
- `can_change_inventory`
- `can_delete_inventory`

### Naming Convention

```
<action>_branch
```

### Examples

- `view_branch`
- `add_branch`
- `change_branch`
- `delete_branch`

---

## 3. Object-Level Permissions

### Scope

These permissions apply to individual instances of models, providing granular control over resources. This is useful for scenarios where users should only access or modify specific records.

### Allowed Actions

Any combination of:

- `view_<model_name>`
- `add_<model_name>`
- `change_<model_name>`
- `delete_<model_name>`

### Naming Convention

```
<action>_<model_name>
```

### Examples

- `view_employee`
- `change_product`
- `delete_invoice`

### Implementation

Typically implemented using a third-party library like `django-guardian` to manage per-object permissions.

---

## Notes & Recommendations

- **Permission Checks:**

  - Use `user.has_perm('app_label.permission_codename')` for general permission checks.
  - For object-level checks, use `user.has_perm('change_modelname', instance)`.

- **Consistency:**

  - Always follow the naming conventions to ensure clear and predictable permission handling.

- **Role Grouping (optional):**

  - Consider defining roles like `branch_manager`, `staff`, or `admin` that group relevant permissions for easier management.

---

End of Document
