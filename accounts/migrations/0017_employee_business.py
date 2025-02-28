# Generated by Django 5.1.4 on 2025-02-28 14:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            """
            0016_alter_phonechangerequest_new_phone_alter_user_groups_and_more
            """,
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="business",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="accounts.business",
            ),
        ),
    ]
