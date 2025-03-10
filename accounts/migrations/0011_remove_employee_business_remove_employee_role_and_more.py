# Generated by Django 5.1.4 on 2025-02-11 15:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_remove_employee_business_employee_business"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="employee",
            name="business",
        ),
        migrations.RemoveField(
            model_name="employee",
            name="role",
        ),
        migrations.CreateModel(
            name="EmployeeBusiness",
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
                    "role",
                    models.CharField(
                        choices=[
                            ("Manager", "Manager"),
                            ("Sales", "Sales"),
                            ("Admin", "Admin"),
                        ],
                        max_length=10,
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
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.employee",
                    ),
                ),
            ],
        ),
    ]
