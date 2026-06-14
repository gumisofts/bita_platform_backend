from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0008_businesspaymentmethod_optional_label_identifier"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="category",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
