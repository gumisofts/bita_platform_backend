# Order Return Workflow

## Overview

The order return workflow allows operators to return all or part of a completed order. A single return event can cover multiple items with arbitrary quantities. The system automatically determines whether the return is **full** or **partial**, restocks eligible inventory, records a refund transaction, and updates the order status — all atomically.

---

## Models

### `OrderReturn`

One record per return event.

| Field                 | Type                                    | Description                             |
| --------------------- | --------------------------------------- | --------------------------------------- |
| `id`                  | UUID                                    | Primary key                             |
| `order`               | FK → `Order`                            | The original completed order            |
| `status`              | `PARTIAL` / `FULL`                      | Auto-determined at return time          |
| `reason`              | TextField (optional)                    | Free-text explanation from the operator |
| `refund_method`       | FK → `BusinessPaymentMethod` (optional) | Payment method used to issue the refund |
| `total_refund_amount` | Decimal                                 | Sum of all line-level refund amounts    |
| `processed_by`        | FK → `Employee` (optional)              | Employee who initiated the return       |

### `OrderReturnItem`

One record per returned line item within a return event.

| Field               | Type               | Description                                      |
| ------------------- | ------------------ | ------------------------------------------------ |
| `id`                | UUID               | Primary key                                      |
| `order_return`      | FK → `OrderReturn` | Parent return event                              |
| `order_item`        | FK → `OrderItem`   | The original order line being returned           |
| `quantity_returned` | PositiveInteger    | Number of units returned                         |
| `is_restocked`      | Boolean            | `True` if `ItemVariant.quantity` was incremented |
| `refund_amount`     | Decimal            | `quantity_returned × variant.selling_price`      |

> **Constraint:** `(order_return, order_item)` is unique — the same line cannot appear twice in one return event.

---

## API

### Endpoint

```
POST /orders/{order_id}/return/
```

Requires authentication and the same business/branch permissions as order management.

### Request body

```json
{
  "items": [
    {
      "order_item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "quantity_returned": 2
    },
    {
      "order_item_id": "7cb93e27-1234-4abc-b3fc-9d741a55bc11",
      "quantity_returned": 1
    }
  ],
  "reason": "Customer changed mind",
  "refund_method": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
}
```

| Field                       | Required | Description                                                         |
| --------------------------- | -------- | ------------------------------------------------------------------- |
| `items`                     | Yes      | At least one line item to return                                    |
| `items[].order_item_id`     | Yes      | UUID of the `OrderItem` to return                                   |
| `items[].quantity_returned` | Yes      | Must be ≥ 1 and ≤ remaining returnable quantity                     |
| `reason`                    | No       | Human-readable reason for the return                                |
| `refund_method`             | No       | UUID of a `BusinessPaymentMethod` belonging to the order's business |

### Success response — `201 Created`

```json
{
  "id": "...",
  "order": "...",
  "status": "FULL",
  "reason": "Customer changed mind",
  "refund_method": "...",
  "total_refund_amount": "150.00",
  "processed_by": "...",
  "processed_by_name": "John Doe",
  "items": [
    {
      "id": "...",
      "order_item": "...",
      "variant_name": "Red - XL",
      "item_name": "T-Shirt",
      "quantity_returned": 2,
      "is_restocked": true,
      "refund_amount": "100.00"
    },
    {
      "id": "...",
      "order_item": "...",
      "variant_name": "Default",
      "item_name": "Mug",
      "quantity_returned": 1,
      "is_restocked": false,
      "refund_amount": "50.00"
    }
  ],
  "created_at": "2026-04-28T13:00:00Z"
}
```

### Error responses

| Status | Condition                                                               |
| ------ | ----------------------------------------------------------------------- |
| `400`  | Order is not in `COMPLETED` status                                      |
| `400`  | An `order_item_id` does not belong to the specified order               |
| `400`  | `quantity_returned` exceeds the still-returnable quantity for that line |
| `400`  | `refund_method` UUID not found for this business                        |
| `500`  | Unexpected error during the atomic transaction                          |

---

## Business Logic

### Pre-conditions

- The order **must** be in `COMPLETED` status. All other statuses (including `RETURNED`) are rejected.
- Each `quantity_returned` is validated against:
  ```
  available = order_item.quantity − sum(previous OrderReturnItem.quantity_returned for that line)
  ```
  This allows the same line to be returned across multiple separate return events (incremental returns), as long as the total never exceeds the original ordered quantity.

### Full vs Partial determination

```
total_ordered        = sum of all order_item.quantity for the order
total_already_returned = sum of all prior OrderReturnItem.quantity_returned for the order
total_now_returning  = sum of quantity_returned in this request

if (total_already_returned + total_now_returning) >= total_ordered:
    status = FULL
else:
    status = PARTIAL
```

### Stock update (`ItemVariant.quantity`)

- Rows are locked with `SELECT FOR UPDATE` before being updated to prevent race conditions.
- Stock is **only** incremented when `item.is_returnable = True`.
- The `is_restocked` flag on `OrderReturnItem` records whether restocking actually occurred for that line.
- Items with `is_returnable = False` still generate a refund but their stock is not restored.

### Financial update (`Transaction`)

A new `Transaction` record of type `REFUND` is created:

| Field               | Value                                       |
| ------------------- | ------------------------------------------- |
| `type`              | `REFUND`                                    |
| `order`             | The original order                          |
| `business`          | Order's business                            |
| `branch`            | Order's branch                              |
| `payment_method`    | The supplied `refund_method` (nullable)     |
| `total_paid_amount` | `total_refund_amount` for this return event |
| `total_left_amount` | `0.00`                                      |

### Order status update

| Return type    | New `Order.status`      |
| -------------- | ----------------------- |
| Full return    | `RETURNED`              |
| Partial return | Unchanged (`COMPLETED`) |

The existing `OrderHistory` signal automatically records the status change whenever `order.status` transitions.

### Atomicity

All of the following happen inside a single `db_transaction.atomic()` block. If any step fails, every change is rolled back:

1. Validate all return lines (before opening the transaction)
2. Lock `ItemVariant` rows
3. Increment `ItemVariant.quantity` for returnable items
4. Create `OrderReturn`
5. Bulk-create `OrderReturnItem` records
6. Create `REFUND` `Transaction`
7. Update `Order.status` (full return only)

---

## State Diagram

```
COMPLETED
    │
    ├─── partial return ──► COMPLETED  (OrderReturn.status = PARTIAL)
    │
    └─── full return    ──► RETURNED   (OrderReturn.status = FULL)
```

Multiple partial returns are allowed on the same order until the cumulative returned quantity equals the total ordered quantity, at which point the next return that completes it will flip the order to `RETURNED`.

---

## Item returnability

| `Item.is_returnable` | Stock restocked | Refund issued |
| -------------------- | --------------- | ------------- |
| `True`               | Yes             | Yes           |
| `False`              | No              | Yes           |

Refunds are always calculated and recorded regardless of returnability. Only inventory restocking is gated behind `is_returnable`.
