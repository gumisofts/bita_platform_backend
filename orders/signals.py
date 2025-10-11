# Signal for creating a transaction when an order is completed
from django.db.models.signals import Signal, post_save
from django.dispatch import receiver

from inventories.signals import on_item_variant_sold
from orders.models import Order

order_completed = Signal()


@receiver(order_completed)
def on_order_completed(sender, instance, **kwargs):
    for item in instance.items.all():
        item.variant.quantity -= item.quantity
        item.variant.save()
