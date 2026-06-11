from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0015_alter_action_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='incident',
            name='external_reference',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
