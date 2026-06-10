from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opencirt', '0008_platform_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='genericioc',
            name='reputation_score',
            field=models.JSONField(blank=True, default=None, null=True),
        ),
    ]
