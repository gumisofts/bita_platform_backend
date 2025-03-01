# flake8: noqa
# Generated by Django 5.1.5 on 2025-02-05 15:04

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0005_alter_item_manufacturer"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupplyReservation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "quantity",
                    models.PositiveIntegerField(
                        validators=[django.core.validators.MinValueValidator(1)]
                    ),
                ),
                ("reserved_at", models.DateTimeField(auto_now_add=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("cancelled", "Cancelled"),
                            ("fulfilled", "Fulfilled"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "supply",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reservations",
                        to="inventory.supply",
                    ),
                ),
            ],
            options={
                "db_table": "supply_reservation",
                "ordering": ["-reserved_at"],
            },
        ),
    ]
