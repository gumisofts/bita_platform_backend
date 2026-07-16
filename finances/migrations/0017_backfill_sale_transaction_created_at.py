from django.db import migrations

BATCH_SIZE = 500


def align_sale_transaction_created_at(apps, schema_editor):
    """SALE transactions created via the order `checkout` flow (as opposed to
    the direct payment-recording flow, which already aligns this correctly)
    were timestamped with whenever the checkout signal fired instead of when
    the order was actually placed. Align them now so period-based reports
    (net_sales, daily breakdowns, etc.) attribute the sale to the right day.
    """
    Transaction = apps.get_model("finances", "Transaction")
    queryset = (
        Transaction.objects.filter(type="SALE", order__isnull=False)
        .select_related("order")
        .only("id", "created_at", "order__created_at")
    )

    to_update = []
    for tx in queryset.iterator():
        if tx.created_at != tx.order.created_at:
            tx.created_at = tx.order.created_at
            to_update.append(tx)
        if len(to_update) >= BATCH_SIZE:
            Transaction.objects.bulk_update(to_update, ["created_at"])
            to_update = []

    if to_update:
        Transaction.objects.bulk_update(to_update, ["created_at"])


def _noop_reverse(apps, schema_editor):
    # Not reversible: we don't know each transaction's original (incorrect)
    # created_at value once overwritten.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0016_alter_transaction_created_at"),
    ]

    operations = [
        migrations.RunPython(align_sale_transaction_created_at, _noop_reverse),
    ]
