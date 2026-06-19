from django.db import migrations
from django.db.models import F


def make_refunds_negative(apps, schema_editor):
    """Existing REFUND transactions were stored as positive magnitudes.

    Refunds are now signed (money paid back to the customer is negative), so
    flip any positive REFUND rows to negative to match the new convention.
    """
    Transaction = apps.get_model("finances", "Transaction")
    Transaction.objects.filter(type="REFUND", total_paid_amount__gt=0).update(
        total_paid_amount=-F("total_paid_amount")
    )


def make_refunds_positive(apps, schema_editor):
    Transaction = apps.get_model("finances", "Transaction")
    Transaction.objects.filter(type="REFUND", total_paid_amount__lt=0).update(
        total_paid_amount=-F("total_paid_amount")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0014_transaction_created_by"),
    ]

    operations = [
        migrations.RunPython(make_refunds_negative, make_refunds_positive),
    ]
