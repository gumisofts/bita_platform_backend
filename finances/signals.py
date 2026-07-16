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
        # Keep the SALE transaction's timestamp aligned with when the order
        # was actually placed, not whenever checkout/completion happened to
        # run — otherwise period-based reports (net_sales, daily breakdowns,
        # etc.) would attribute the sale to the wrong day.
        created_at=instance.created_at,
    )


def _is_credit_payment_method(bpm) -> bool:
    """Return True if this BusinessPaymentMethod represents a deferred-credit/debt."""
    if bpm.identifier and bpm.identifier.upper() == "CREDIT":
        return True
    if bpm.payment_id and bpm.payment.name and bpm.payment.name.upper() == "CREDIT":
        return True
    return False


@receiver(post_save, sender="inventories.Supply")
def create_supply_transaction(sender, instance, created, **kwargs):
    """
    Create a financial transaction when a Supply is saved with a payment method.

    - Credit / debt payment  →  DEBT transaction (liability, no cash moved)
    - Any other payment       →  PURCHASE transaction (actual expense)

    A debt can later be settled via the ``settle_debt`` action on SupplyViewset,
    which creates a PURCHASE transaction with category ``supply:<id>:paid``.
    """
    if not instance.payment_method_id:
        return

    # Avoid duplicate transactions if the supply record is re-saved later.
    supply_ref = f"supply:{instance.id}"
    if Transaction.objects.filter(category=supply_ref).exists():
        return

    # Select_related so _is_credit_payment_method can access payment.name without extra query.
    bpm = (
        instance.payment_method
        if hasattr(instance.payment_method, "payment")
        else instance.payment_method.__class__.objects.select_related("payment").get(
            pk=instance.payment_method_id
        )
    )

    tx_type = (
        Transaction.TransactionType.DEBT
        if _is_credit_payment_method(bpm)
        else Transaction.TransactionType.PURCHASE
    )

    Transaction.objects.create(
        type=tx_type,
        total_paid_amount=instance.total_cost,
        payment_method=instance.payment_method,
        business=instance.business,
        branch=instance.branch,
        category=supply_ref,
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
