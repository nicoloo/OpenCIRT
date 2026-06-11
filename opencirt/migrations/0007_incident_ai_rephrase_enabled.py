from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0006_auditlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='incident',
            name='ai_rephrase_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
