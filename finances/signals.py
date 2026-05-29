from django.db.models.signals import post_save
from django.dispatch import receiver

from finances.models import Transaction
from orders.signals import order_completed

from .models import BusinessPaymentMethod, PaymentMethod


@receiver(order_completed)
def create_transaction(sender, instance, **kwargs):
    created_by = instance.employee.user if instance.employee_id else None
    Transaction.objects.create(
        order=instance,
        type=Transaction.TransactionType.SALE,
        total_paid_amount=instance.total_payable,
        payment_method=instance.payment_method,
        business=instance.business,
        branch=instance.branch,
        created_by=created_by,
    )


@receiver(post_save, sender="business.Branch")
def auto_create_cash_and_credit_payment_methods(sender, instance, created, **kwargs):

    if created:
        BusinessPaymentMethod.objects.create(
            business=instance.business,
            payment=PaymentMethod.get_or_create_cash_payment_method(),
            branch=instance,
            identifier="CASH",
            label="Cash",
        )
        BusinessPaymentMethod.objects.create(
            business=instance.business,
            payment=PaymentMethod.get_or_create_credit_payment_method(),
            branch=instance,
            identifier="CREDIT",
            label="Credit",
        )
