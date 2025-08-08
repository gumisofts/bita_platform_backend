from django.db.models.signals import post_save
from django.dispatch import Signal 
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Max
from inventories.models import Item, ItemVariant, SuppliedItem


item_variant_price_changed = Signal()
item_variant_sold = Signal()


@receiver(post_save, sender=SuppliedItem)
def on_supplied_item_created(sender, instance, created, **kwargs):
    if created:
        instance.variant.quantity += instance.quantity
        instance.variant.save()
        max_price= instance.variant.aggregate(max_selling_price=Max('selling_price'))['max_selling_price']
        if max_price != instance.variant.selling_price:
            instance.variant.selling_price = max_price
            instance.variant.save()
            item_variant_price_changed.send(sender=instance.variant.__class__, instance=instance.variant)

@receiver(item_variant_sold)
def on_item_variant_sold(sender, instance, **kwargs):
    instance.variant.quantity -= instance.quantity
    instance.variant.save()