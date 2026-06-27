# Signal for creating a transaction when an order is completed
from django.core.exceptions import ValidationError
from django.db.models.signals import Signal, post_save, pre_save
from django.dispatch import receiver

from inventories.signals import on_item_variant_sold
from orders.models import Order, OrderHistory

order_completed = Signal()


@receiver(order_completed)
def on_order_completed_receipt(sender, instance, **kwargs):
    from django.db import transaction

    from orders.tasks import generate_order_receipt_task

    order_id = str(instance.id)
    transaction.on_commit(lambda: generate_order_receipt_task.delay(order_id))


@receiver(order_completed)
def on_order_completed(sender, instance, **kwargs):
    from inventories.models import ItemVariant, SuppliedItem

    items = list(instance.items.select_related("variant", "supplied_item").all())
    variant_ids = [item.variant_id for item in items]

    # Lock all variant rows upfront in one query.
    locked_variants = {
        v.pk: v
        for v in ItemVariant.objects.select_for_update().filter(pk__in=variant_ids)
    }

    # Lock supplied items that are explicitly set on order items (direct batch deduction).
    direct_supplied_ids = [
        item.supplied_item_id for item in items if item.supplied_item_id
    ]
    locked_direct = (
        {
            s.pk: s
            for s in SuppliedItem.objects.select_for_update().filter(
                pk__in=direct_supplied_ids
            )
        }
        if direct_supplied_ids
        else {}
    )

    # For items with no specific batch, lock all non-empty batches for those variants
    # upfront (FIFO drain, oldest first). One query for all FIFO variants.
    fifo_variant_ids = [item.variant_id for item in items if not item.supplied_item_id]
    fifo_batches_by_variant: dict = {}
    if fifo_variant_ids:
        for batch in (
            SuppliedItem.objects.select_for_update()
            .filter(variant_id__in=fifo_variant_ids, quantity__gt=0)
            .order_by("variant_id", "created_at")
        ):
            fifo_batches_by_variant.setdefault(batch.variant_id, []).append(batch)

    # Validate stock availability before touching anything.
    insufficient = []
    for item in items:
        variant = locked_variants[item.variant_id]
        if variant.quantity < item.quantity:
            insufficient.append(
                f"'{variant.name}': need {item.quantity}, have {variant.quantity}"
            )

    if insufficient:
        raise ValidationError("Insufficient stock for: " + "; ".join(insufficient))

    # All checks passed — decrement variant totals and the correct batch quantities.
    for item in items:
        variant = locked_variants[item.variant_id]
        variant.quantity -= item.quantity
        variant.save(update_fields=["quantity", "updated_at"])

        if item.supplied_item_id and item.supplied_item_id in locked_direct:
            # Deduct directly from the specific batch linked to this order item.
            batch = locked_direct[item.supplied_item_id]
            batch.quantity = max(0, batch.quantity - item.quantity)
            batch.save(update_fields=["quantity", "updated_at"])
        else:
            # No specific batch — drain FIFO across the variant's batches.
            remaining = item.quantity
            for batch in fifo_batches_by_variant.get(item.variant_id, []):
                if remaining <= 0:
                    break
                deduct = min(batch.quantity, remaining)
                batch.quantity -= deduct
                batch.save(update_fields=["quantity", "updated_at"])
                remaining -= deduct


@receiver(pre_save, sender=Order)
def track_order_changes(sender, instance, **kwargs):
    """
    Track changes to Order model and create OrderHistory records.
    Stores the old instance in the instance to be used in post_save.
    """
    if instance.pk:  # Only track changes for existing orders
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            # Store old instance on the new instance for use in post_save
            instance._old_instance = old_instance
        except Order.DoesNotExist:
            # Order doesn't exist yet, this is a new order
            instance._old_instance = None


@receiver(post_save, sender=Order)
def create_order_history(sender, instance, created, **kwargs):
    """
    Create OrderHistory records after an order is saved.
    """
    if created:
        # For new orders, create an initial history entry
        OrderHistory.objects.create(
            order=instance,
            field_name="created",
            old_value=None,
            new_value="Order created",
        )
        from django.db import transaction

        from orders.tasks import generate_order_receipt_task

        order_id = str(instance.id)
        transaction.on_commit(lambda: generate_order_receipt_task.delay(order_id))
        return

    # For updates, track field changes
    if hasattr(instance, "_old_instance") and instance._old_instance:
        old_instance = instance._old_instance
        tracked_fields = [
            "status",
            "total_payable",
            "customer",
            "employee",
            "payment_method",
            "business",
            "branch",
        ]

        for field_name in tracked_fields:
            old_value = getattr(old_instance, field_name, None)
            new_value = getattr(instance, field_name, None)

            # Convert ForeignKey objects to their string representation or ID
            if hasattr(old_value, "pk"):
                old_value = str(old_value.pk) if old_value else None
            if hasattr(new_value, "pk"):
                new_value = str(new_value.pk) if new_value else None

            # Convert to string for storage
            old_value_str = str(old_value) if old_value is not None else None
            new_value_str = str(new_value) if new_value is not None else None

            # Only create history if the value actually changed
            if old_value_str != new_value_str:
                # Try to get user from thread-local storage if available
                # This can be set in middleware or views
                changed_by = None
                changed_by_employee = None

                try:
                    import threading

                    if hasattr(threading.current_thread(), "user"):
                        user = threading.current_thread().user
                        if user and user.is_authenticated:
                            changed_by = user
                            # Try to get employee
                            try:
                                from business.models import Employee

                                changed_by_employee = Employee.objects.filter(
                                    user=user, business=instance.business
                                ).first()
                            except:
                                pass
                except:
                    pass

                OrderHistory.objects.create(
                    order=instance,
                    field_name=field_name,
                    old_value=old_value_str,
                    new_value=new_value_str,
                    changed_by=changed_by,
                    changed_by_employee=changed_by_employee,
                )

        # Clean up the stored old instance
        if hasattr(instance, "_old_instance"):
            delattr(instance, "_old_instance")

    # Regenerate receipt whenever the order is created or meaningfully updated.
    # Skip the update_fields=["receipt"] save the task does itself to avoid loops.
    # Use on_commit so the task only fires after the transaction commits — dispatching
    # Celery inside an atomic block causes the whole transaction to roll back if
    # the broker is momentarily unavailable.
    update_fields = kwargs.get("update_fields")
    if update_fields is None or "receipt" not in update_fields:
        from django.db import transaction

        from orders.tasks import generate_order_receipt_task

        order_id = str(instance.id)
        transaction.on_commit(lambda: generate_order_receipt_task.delay(order_id))
