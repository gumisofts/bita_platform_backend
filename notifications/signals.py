import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from inventories.models import Item, SuppliedItem
from inventories.signals import item_variant_price_changed
from orders.signals import order_completed

from .service import create_notification
from .tasks import check_low_stock_task

logger = logging.getLogger(__name__)


# ── Restock ──────────────────────────────────────────────────────────────────
@receiver(post_save, sender=SuppliedItem)
def on_restocked(sender, instance, created, **kwargs):
    """Notify when new stock arrives (SuppliedItem created)."""
    if not created:
        return
    item = instance.item
    variant = instance.variant
    if not item:
        return

    create_notification(
        title="Restocked",
        message=(
            f"{item.name} ({variant.name}) has been restocked "
            f"with {instance.quantity} units."
        ),
        event_type="restocked",
        business=instance.business,
        notification_type="success",
        data={
            "item_id": str(item.id),
            "variant_id": str(variant.id),
            "item_name": item.name,
            "variant_name": variant.name,
            "quantity_added": instance.quantity,
            "supply_id": str(instance.supply_id),
        },
    )


# ── Price Change ─────────────────────────────────────────────────────────────
@receiver(item_variant_price_changed)
def on_price_changed(sender, instance, **kwargs):
    """Notify when a variant's selling price changes."""
    variant = instance
    item = variant.item

    create_notification(
        title="Price Change",
        message=(
            f"The price for {item.name} ({variant.name}) "
            f"has been updated to {variant.selling_price}."
        ),
        event_type="price_change",
        business=item.business,
        notification_type="info",
        data={
            "item_id": str(item.id),
            "variant_id": str(variant.id),
            "item_name": item.name,
            "variant_name": variant.name,
            "new_price": str(variant.selling_price),
        },
    )


# ── Order Completed → Low-Stock Check ───────────────────────────────────────
@receiver(order_completed)
def on_order_completed_check_stock(sender, instance, **kwargs):
    """
    After an order is completed, schedule an async check to see if any
    of the sold variants have dropped below their low-stock threshold.
    The Celery task runs after the DB transaction commits so all quantity
    decrements are already persisted.
    """
    order = instance
    variant_ids = list(order.items.values_list("variant_id", flat=True))
    if not variant_ids:
        return

    id_strings = [str(vid) for vid in variant_ids]
    business_id = str(order.business_id)
    transaction.on_commit(lambda: check_low_stock_task.delay(id_strings, business_id))


# ── Order Completed → Notification ──────────────────────────────────────────
@receiver(order_completed)
def on_order_completed_notify(sender, instance, **kwargs):
    """Create a notification when an order is completed."""
    order = instance
    create_notification(
        title="Order Completed",
        message=f"Order #{str(order.id)[:8]} has been completed — total: {order.total_payable}.",
        event_type="order_completed",
        business=order.business,
        notification_type="success",
        data={
            "order_id": str(order.id),
            "total_payable": str(order.total_payable),
        },
    )


# ── Product Updated ─────────────────────────────────────────────────────────
@receiver(post_save, sender=Item)
def on_product_updated(sender, instance, created, **kwargs):
    """
    Notify when a product's details are updated via the API.
    Skips newly created items (no need to alert on creation).
    """
    if created:
        return

    create_notification(
        title="Product Updated",
        message=f"{instance.name} has been updated.",
        event_type="product_updated",
        business=instance.business,
        notification_type="info",
        data={
            "item_id": str(instance.id),
            "item_name": instance.name,
        },
        deduplicate_key="item_id",
        deduplicate_window_hours=1,
    )


# ── Inventory Movement ──────────────────────────────────────────────────────
@receiver(post_save, sender="inventories.InventoryMovement")
def on_inventory_movement_status_changed(sender, instance, created, **kwargs):
    """Notify on inventory movement creation or status changes."""
    if created:
        msg = (
            f"New inventory movement {instance.movement_number} requested "
            f"from {instance.from_branch} to {instance.to_branch}."
        )
    elif instance.status in ("approved", "shipped", "received", "cancelled"):
        msg = (
            f"Inventory movement {instance.movement_number} "
            f"status changed to {instance.get_status_display()}."
        )
    else:
        return

    create_notification(
        title="Inventory Movement",
        message=msg,
        event_type="inventory_movement",
        business=instance.business,
        notification_type="info",
        data={
            "movement_id": str(instance.id),
            "movement_number": instance.movement_number,
            "status": instance.status,
            "from_branch": str(instance.from_branch_id),
            "to_branch": str(instance.to_branch_id),
        },
    )
