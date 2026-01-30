# Generated manually for optional label and identifier

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0007_alter_businesspaymentmethod_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="businesspaymentmethod",
            name="label",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="businesspaymentmethod",
            name="identifier",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
