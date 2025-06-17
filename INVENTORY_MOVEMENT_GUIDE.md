# Inventory Movement Between Branches

This document describes the new inventory movement system that allows transferring items between different branches of a business.

## Overview

The inventory movement system provides a structured workflow for moving inventory items from one branch to another. It includes approval workflows, tracking, and automatic inventory updates.

## Models

### InventoryMovement
The main model that tracks a movement request between branches.

**Fields:**
- `movement_number`: Unique identifier (auto-generated: MOV-YYYYMMDD-XXXX)
- `from_branch`: Source branch
- `to_branch`: Destination branch
- `business`: The business (auto-set from branches)
- `status`: Current status (pending, approved, shipped, received, cancelled)
- `requested_by`: User who requested the movement
- `approved_by`: User who approved the movement
- `shipped_by`: User who marked as shipped
- `received_by`: User who marked as received
- `notes`: Optional notes
- Timestamps for each status change

### InventoryMovementItem
Individual items included in a movement.

**Fields:**
- `movement`: Reference to the movement
- `supplied_item`: The item being moved
- `quantity_requested`: Requested quantity
- `quantity_shipped`: Actually shipped quantity
- `quantity_received`: Actually received quantity
- `notes`: Optional item-specific notes

## Workflow

### 1. Request Movement (Status: pending)
Create a new movement request with items to transfer.

```http
POST /api/inventories/movements/
{
  "from_branch": "branch-uuid",
  "to_branch": "branch-uuid", 
  "notes": "Monthly stock redistribution",
  "items": [
    {
      "supplied_item_id": "item-uuid",
      "quantity": 50,
      "notes": "High demand item"
    }
  ]
}
```

### 2. Approve Movement (Status: approved)
A manager or owner approves the movement request.

```http
POST /api/inventories/movements/{movement_id}/approve/
```

### 3. Ship Movement (Status: shipped)
Mark items as shipped and reduce inventory from source branch.

```http
POST /api/inventories/movements/{movement_id}/ship/
{
  "items": [
    {
      "movement_item_id": "item-uuid",
      "quantity_shipped": 45
    }
  ]
}
```

### 4. Receive Movement (Status: received)
Mark items as received and add inventory to destination branch.

```http
POST /api/inventories/movements/{movement_id}/receive/
{
  "items": [
    {
      "movement_item_id": "item-uuid", 
      "quantity_received": 45
    }
  ]
}
```

### 5. Cancel Movement (Status: cancelled)
Cancel a pending or approved movement.

```http
POST /api/inventories/movements/{movement_id}/cancel/
```

## API Endpoints

### List Movements
```http
GET /api/inventories/movements/
```

**Query Parameters:**
- `business_id`: Filter by business
- `branch_id`: Filter by branch (source or destination)
- `status`: Filter by status

### Create Movement
```http
POST /api/inventories/movements/
```

### Get Movement Details
```http
GET /api/inventories/movements/{movement_id}/
```

### Update Movement
```http
PUT /api/inventories/movements/{movement_id}/
PATCH /api/inventories/movements/{movement_id}/
```

### Status Actions
- `POST /api/inventories/movements/{movement_id}/approve/`
- `POST /api/inventories/movements/{movement_id}/ship/`
- `POST /api/inventories/movements/{movement_id}/receive/`
- `POST /api/inventories/movements/{movement_id}/cancel/`

## Permissions

The system respects the existing role-based permissions:

- **Owner**: Full access to all movements
- **Manager**: Full access to movements for their business
- **Employee**: Access to movements for their business/branch

## Business Rules

1. **Same Business Only**: Movements can only occur between branches of the same business
2. **Different Branches**: Source and destination branches must be different
3. **Stock Validation**: Cannot request more items than available in source branch
4. **Status Flow**: Movements must follow the status progression (pending → approved → shipped → received)
5. **Quantity Validation**: 
   - Shipped quantity cannot exceed requested quantity
   - Received quantity cannot exceed shipped quantity

## Inventory Updates

### On Shipping
- Reduces inventory quantity in source branch's `SuppliedItem`

### On Receiving
- Creates or updates `Supply` in destination branch
- Creates new `SuppliedItem` in destination branch (or adds to existing if same batch/product)
- Handles product number conflicts by appending transfer ID

## Example Usage

### Complete Movement Flow

```python
# 1. Create movement request
movement_data = {
    "from_branch": "branch-a-uuid",
    "to_branch": "branch-b-uuid",
    "notes": "Restocking for high demand items",
    "items": [
        {
            "supplied_item_id": "item-1-uuid",
            "quantity": 25,
            "notes": "Popular item"
        },
        {
            "supplied_item_id": "item-2-uuid", 
            "quantity": 10
        }
    ]
}

# 2. POST to create movement
response = requests.post('/api/inventories/movements/', data=movement_data)
movement_id = response.json()['id']

# 3. Approve movement
requests.post(f'/api/inventories/movements/{movement_id}/approve/')

# 4. Ship movement
ship_data = {
    "items": [
        {"movement_item_id": "item-1-id", "quantity_shipped": 25},
        {"movement_item_id": "item-2-id", "quantity_shipped": 8}  # Partial shipment
    ]
}
requests.post(f'/api/inventories/movements/{movement_id}/ship/', data=ship_data)

# 5. Receive movement
receive_data = {
    "items": [
        {"movement_item_id": "item-1-id", "quantity_received": 25},
        {"movement_item_id": "item-2-id", "quantity_received": 8}
    ]
}
requests.post(f'/api/inventories/movements/{movement_id}/receive/', data=receive_data)
```

## Admin Interface

The Django admin interface provides additional management capabilities:

- View all movements with filtering by status, business, and date
- Search movements by number, branch names
- Readonly fields for audit trail (approval timestamps, user tracking)

## Testing

Comprehensive tests are included covering:

- Movement creation and validation
- Status transitions
- Inventory updates
- Permission checks
- Error handling

Run tests with:
```bash
python manage.py test inventories.tests.InventoryMovementTest
```

## Migration

After implementing the changes, run:

```bash
python manage.py makemigrations inventories
python manage.py migrate
```

This will create the necessary database tables for the inventory movement functionality. 