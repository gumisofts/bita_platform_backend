from django.db.models.signals import post_save
from django.dispatch import receiver

from finances.models import Transaction
from orders.signals import order_completed


@receiver(order_completed)
def create_transaction(sender, instance, **kwargs):
    Transaction.objects.create(
        order=instance,
        type=Transaction.TransactionType.SALE,
        total_paid_amount=instance.total_payable,
        payment_method=instance.payment_method,
        business=instance.business,
        branch=instance.branch,
    )
