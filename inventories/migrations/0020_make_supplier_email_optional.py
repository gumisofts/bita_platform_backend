# Generated manually for making supplier email optional

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventories", "0019_make_description_optional"),
    ]

    operations = [
        migrations.AlterField(
            model_name="supplier",
            name="email",
            field=models.EmailField(blank=True, null=True),
        ),
    ]
