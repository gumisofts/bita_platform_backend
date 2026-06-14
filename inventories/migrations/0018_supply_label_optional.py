# Generated manually for supply label optional

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventories", "0017_alter_itemvariant_sku"),
    ]

    operations = [
        migrations.AlterField(
            model_name="supply",
            name="label",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
