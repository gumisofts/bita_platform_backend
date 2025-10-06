from django.db.models import Max, Q
from django.db.models.signals import post_save, pre_delete
from django.dispatch import Signal, receiver
from django.utils import timezone

from inventories.models import Item, ItemVariant, SuppliedItem

item_variant_price_changed = Signal()
item_variant_sold = Signal()


@receiver(post_save, sender=SuppliedItem)
def on_supplied_item_created(sender, instance, created, **kwargs):
    if created:
        instance.supply.no_of_items += 1
        instance.supply.total_cost += instance.quantity * instance.selling_price
        instance.supply.save()
        instance.variant.quantity += instance.quantity
        instance.variant.save()
        max_price = SuppliedItem.objects.filter(
            variant=instance.variant, quantity__gt=0
        ).aggregate(max_selling_price=Max("selling_price"))["max_selling_price"]
        if max_price != instance.variant.selling_price:
            instance.variant.selling_price = max_price
            instance.variant.save()
            item_variant_price_changed.send(
                sender=instance.variant.__class__, instance=instance.variant
            )


@receiver(item_variant_sold)
def on_item_variant_sold(sender, instance, **kwargs):
    instance.variant.quantity -= instance.quantity
    instance.variant.save()


@receiver(pre_delete, sender=SuppliedItem)
def on_supplied_item_deleted(sender, instance, **kwargs):
    instance.variant.quantity -= instance.quantity
    instance.variant.save()
    max_price = SuppliedItem.objects.filter(
        Q(variant=instance.variant, quantity__gt=0) & ~Q(variant_id=instance.variant.id)
    ).aggregate(max_selling_price=Max("selling_price"))["max_selling_price"]
    if max_price != instance.variant.selling_price:
        instance.variant.selling_price = max_price
        instance.variant.save()
        item_variant_price_changed.send(
            sender=instance.variant.__class__, instance=instance.variant
        )
