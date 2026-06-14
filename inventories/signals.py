from django.db.models import Max, Q
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import Signal, receiver
from django.utils import timezone

from inventories.models import Item, ItemVariant, SuppliedItem

item_variant_price_changed = Signal()
item_variant_sold = Signal()


@receiver(pre_save, sender=SuppliedItem)
def capture_supplied_item_old_price(sender, instance, **kwargs):
    """Store the pre-update selling_price so post_save can detect changes."""
    if instance.pk:
        instance._old_selling_price = (
            SuppliedItem.objects.filter(pk=instance.pk)
            .values_list("selling_price", flat=True)
            .first()
        )
    else:
        instance._old_selling_price = None


@receiver(post_save, sender=SuppliedItem)
def on_supplied_item_saved(sender, instance, created, **kwargs):
    if created:
        instance.supply.no_of_items += 1
        instance.supply.total_cost += instance.quantity * instance.purchase_price
        instance.supply.save()
        instance.variant.quantity += instance.quantity
        instance.variant.save()
        return

    # Fire price change notification when selling_price is updated on an existing supply.
    old_price = getattr(instance, "_old_selling_price", None)
    if old_price is not None and old_price != instance.selling_price:
        item_variant_price_changed.send(sender=instance.__class__, instance=instance)


@receiver(item_variant_sold)
def on_item_variant_sold(sender, instance, **kwargs):
    instance.variant.quantity -= instance.quantity
    instance.variant.save()


@receiver(pre_delete, sender=SuppliedItem)
def on_supplied_item_deleted(sender, instance, **kwargs):
    # Use max(0, ...) to prevent going negative during cascade deletes (e.g. business
    # deletion), where multiple SuppliedItems for the same variant are each decremented
    # in sequence while the variant hasn't been removed from the DB yet.
    instance.variant.quantity = max(0, instance.variant.quantity - instance.quantity)
    instance.variant.save()
