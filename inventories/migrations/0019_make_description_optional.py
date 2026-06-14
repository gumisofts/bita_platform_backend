# Generated manually for making description optional

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventories", "0018_supply_label_optional"),
    ]

    operations = [
        migrations.AlterField(
            model_name="group",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="item",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
    ]
