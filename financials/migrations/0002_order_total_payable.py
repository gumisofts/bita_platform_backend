# Generated by Django 5.1.4 on 2025-03-12 19:26

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("financials", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="total_payable",
            field=models.DecimalField(
                decimal_places=2, default=Decimal("0.00"), max_digits=10
            ),
        ),
    ]
