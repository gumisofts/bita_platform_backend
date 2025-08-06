from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from inventories.models import Item, ItemVariant, SuppliedItem


@receiver(post_save, sender=SuppliedItem)
def create_stock_movement(sender, instance, created, **kwargs):
    if created:
        instance.variant.quantity += instance.quantity
        instance.variant.save()
