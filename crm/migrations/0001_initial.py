# Generated by Django 5.1.4 on 2025-03-11 17:42
import uuid

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("email", models.EmailField(max_length=254, unique=True)),
                (
                    "phone_number",
                    models.CharField(
                        blank=True,
                        max_length=15,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Phone number must be entered in the format:                     '912345678 / 712345678'. Up to 9 digits allowed.",
                                regex="^(9|7)\\d{8}$",
                            )
                        ],
                    ),
                ),
                ("full_name", models.CharField(max_length=255)),
                (
                    "business",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.business",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GiftCard",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("redeemed", models.BooleanField(default=False)),
                ("redeemed_at", models.DateTimeField(null=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "type",
                    models.IntegerField(
                        choices=[
                            (1, "Specific Item"),
                            (2, "Business Item"),
                            (3, "Platform Item"),
                        ]
                    ),
                ),
                (
                    "business",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.business",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_giftcards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
