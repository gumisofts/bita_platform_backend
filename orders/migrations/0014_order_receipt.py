from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0013_alter_order_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="receipt",
            field=models.FileField(blank=True, null=True, upload_to="receipts/"),
        ),
    ]
