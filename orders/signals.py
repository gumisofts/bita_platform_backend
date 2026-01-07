# Signal for creating a transaction when an order is completed
from django.db.models.signals import Signal, post_save, pre_save
from django.dispatch import receiver

from inventories.signals import on_item_variant_sold
from orders.models import Order, OrderHistory

order_completed = Signal()


@receiver(order_completed)
def on_order_completed(sender, instance, **kwargs):
    for item in instance.items.all():
        item.variant.quantity -= item.quantity
        item.variant.save()


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
