from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_userdevice_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="telegram_id",
            field=models.BigIntegerField(
                blank=True, db_index=True, null=True, unique=True
            ),
        ),
    ]
