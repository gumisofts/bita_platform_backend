# Generated by Django 5.1.4 on 2025-02-01 08:53

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_remove_user_username_alter_user_email_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
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
                ("first_name", models.CharField(max_length=255)),
                ("last_name", models.CharField(max_length=255)),
                (
                    "phone",
                    models.CharField(
                        max_length=15,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Phone number must be \
                                    entered in the format: \
                                    '912345678 / 712345678'. \
                                    Up to 9 digits allowed.",
                                regex="^(9|7)\\d{8}$",
                            )
                        ],
                    ),
                ),
                ("email", models.EmailField(max_length=254)),
                ("address", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="Supplier",
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
                ("name", models.CharField(max_length=255)),
                (
                    "phone",
                    models.CharField(
                        max_length=15,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Phone number must be \
                                    entered in the format: \
                                    '912345678 / 712345678'. \
                                    Up to 9 digits allowed.",
                                regex="^(9|7)\\d{8}$",
                            )
                        ],
                    ),
                ),
                ("email", models.EmailField(max_length=254)),
                ("address", models.TextField()),
            ],
        ),
    ]
